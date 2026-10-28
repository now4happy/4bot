"""Review and repair an update branch without changing the running checkout.

CLI first previews; --apply plus explicit --discard paths repairs that same branch.
"""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import time
import uuid
from types import SimpleNamespace


class RepairError(RuntimeError):
    pass


def checked(host, *args):
    rc, text = host.git(*args)
    if rc:
        # Do not expose Git output: hooks/remote URLs can contain credentials.
        raise RepairError('Git 작업 실패: ' + args[0] + ' (코드 ' + str(rc) + ')')
    return text.strip()


def snapshot(host, branch, expected=None, main_expected=None):
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._/-]*', branch) or branch in ('main', 'HEAD'):
        raise RepairError('main 이외의 업데이트 브랜치만 정리할 수 있습니다.')
    checked(host, 'check-ref-format', 'refs/heads/' + branch)
    checked(host, 'fetch', '-q', 'origin',
            '+refs/heads/main:refs/remotes/origin/main',
            '+refs/heads/' + branch + ':refs/remotes/origin/' + branch)
    head = checked(host, 'rev-parse', 'HEAD')
    main = checked(host, 'rev-parse', 'refs/remotes/origin/main')
    sha = checked(host, 'rev-parse', 'refs/remotes/origin/' + branch)
    if expected and expected != sha:
        raise RepairError('브랜치가 바뀌었습니다. 충돌 정리를 다시 열어 주세요.')
    if main_expected and main_expected != main:
        raise RepairError('main이 바뀌었습니다. 정리 대상을 다시 확인해 주세요.')
    if head != main:
        if host.git('merge-base', '--is-ancestor', head, main)[0] == 0:
            raise RepairError('GitHub main에 서버를 거치지 않은 수정이 있습니다 (main이 서버보다 앞섬). '
                              '충돌 정리로는 고치지 않습니다. GitHub에서 main 기준 새 브랜치를 만들어 '
                              '6. Update 알림으로 먼저 승인하세요.')
        if host.git('merge-base', '--is-ancestor', main, head)[0] == 0:
            raise RepairError('서버에 적용된 결과가 아직 GitHub main에 올라가지 않았습니다 (서버가 앞섬). '
                              '직전 업데이트 완료 알림의 main 업로드 결과를 먼저 확인해야 합니다.')
        raise RepairError('서버 HEAD와 GitHub main이 서로 다른 수정으로 갈라졌습니다. '
                          '자동으로 고치지 않습니다. 어떤 수정이 어디에 있는지 먼저 확인해야 합니다.')
    if checked(host, 'status', '--porcelain', '--untracked-files=no'):
        raise RepairError('서버에 미기록 변경 또는 미해결 충돌이 있습니다. 먼저 보존·확인이 필요합니다.')
    for name in ('MERGE_HEAD', 'CHERRY_PICK_HEAD', 'REVERT_HEAD'):
        if host.git('rev-parse', '-q', '--verify', name)[0] == 0:
            raise RepairError('서버에 진행 중인 Git 작업이 있습니다. 자동으로 취소하지 않습니다.')
    paths = checked(host, 'diff', '--name-only', '-z', main + '...' + sha).split('\0')
    paths = [p for p in paths if p]
    if not paths:
        raise RepairError('정리할 업데이트 변경이 없습니다.')
    # Paths are passed after --, never interpolated into a shell command.
    if any('\n' in p or '\r' in p for p in paths):
        raise RepairError('표시할 수 없는 파일명이 있어 수동 확인이 필요합니다.')
    return {'branch': branch, 'sha': sha, 'main': main, 'paths': paths}


def build(host, plan, discard, publish=False):
    """Merge main into the existing branch and resolve only explicitly chosen paths."""
    if not set(discard) <= set(plan['paths']):
        raise RepairError('선택한 파일이 현재 업데이트 목록과 다릅니다.')
    with tempfile.TemporaryDirectory(prefix='updater-conflicts-') as parent:
        owner = getattr(host, 'OWNER', None)
        if os.geteuid() == 0 and owner:
            os.chown(parent, owner.pw_uid, owner.pw_gid)
        work = os.path.join(parent, 'tree')
        added = False
        try:
            checked(host, 'worktree', 'add', '--detach', work, plan['sha'])
            added = True
            rc, _ = host.git('-C', work, 'merge', '--no-commit', '--no-ff', plan['main'])
            unresolved = checked(host, '-C', work, 'diff', '--name-only', '--diff-filter=U').splitlines()
            if rc and not unresolved:
                raise RepairError('임시 병합을 진행할 수 없습니다. Git 설정을 확인해 주세요.')
            if not publish:
                return {'conflicts': unresolved}
            for path in discard:
                if host.git('cat-file', '-e', plan['main'] + ':' + path)[0]:
                    # restore cannot remove a modify/delete unmerged entry.
                    # Remove only the explicitly selected path in the temp tree.
                    checked(host, '-C', work, 'rm', '-f', '--ignore-unmatch', '--', path)
                else:
                    checked(host, '-C', work, 'restore', '--source=' + plan['main'],
                            '--staged', '--worktree', '--', path)
            remaining = checked(host, '-C', work, 'diff', '--name-only', '--diff-filter=U').splitlines()
            if remaining:
                raise RepairError('선택하지 않은 충돌이 남아 정리를 중단했습니다: ' + ', '.join(remaining))
            # Verify changed Python files statically. Never import or execute bot code.
            changed = checked(host, '-C', work, 'diff', '--name-only', '-z',
                              plan['main']).split('\0')
            for path in changed:
                if path.endswith('.py'):
                    rc, source = host.git('-C', work, 'show', ':' + path)
                    if rc == 0:
                        try:
                            compile(source, path, 'exec')
                        except SyntaxError:
                            raise RepairError('정리 후 Python 문법 오류: ' + path)
            # A merge may already be up-to-date; require an actual new commit.
            merge_open = host.git('-C', work, 'rev-parse', '-q', '--verify', 'MERGE_HEAD')[0] == 0
            staged = checked(host, '-C', work, 'diff', '--cached', '--name-only')
            if not merge_open and not staged:
                raise RepairError('변경 사항이 없어 브랜치를 수정하지 않았습니다.')
            checked(host, '-C', work, 'commit', '-qm',
                    'update: main 기준으로 선택한 이전 변경 정리')
            repaired = checked(host, '-C', work, 'rev-parse', 'HEAD')
            checked(host, 'merge-base', '--is-ancestor', plan['sha'], repaired)
            checked(host, 'merge-base', '--is-ancestor', plan['main'], repaired)
            # Recheck both snapshots before writing; a normal fast-forward push also
            # rejects a concurrent staging update. No force push or working-tree reset.
            snapshot(host, plan['branch'], plan['sha'], plan['main'])
            stamp = time.strftime('%Y%m%d-%H%M%S', time.gmtime()) + '-' + uuid.uuid4().hex[:8]
            backup = 'updater-backup/' + stamp
            checked(host, 'push', '--atomic', 'origin',
                    plan['sha'] + ':refs/tags/' + backup,
                    repaired + ':refs/heads/' + plan['branch'])
            return {'sha': repaired, 'backup': backup,
                    'files': [p for p in changed if p], 'discarded': list(discard)}
        finally:
            if added:
                # Only the isolated disposable worktree is removed, never REPO.
                host.git('worktree', 'remove', '--force', work)


def preview(host, state, offer_key):
    offer = state.get('offers', {}).get(offer_key)
    if not offer:
        return host.say('⚠️ 최신 업데이트 알림에서 다시 눌러 주세요.')
    try:
        plan = snapshot(host, offer['branch'], offer['sha'])
        result = build(host, plan, [], publish=False)
        if len(plan['paths']) > 30:
            raise RepairError('변경 파일이 30개를 넘어 파일별 수동 검토가 필요합니다.')
        plan.update(selected=[], at=time.time(), offer_key=offer_key,
                    conflicts=result['conflicts'])
        token = uuid.uuid4().hex[:12]
        state.setdefault('conflict_plans', {})[token] = plan
        state['conflict_plans'] = {k: v for k, v in state['conflict_plans'].items()
                                   if time.time() - v.get('at', 0) < 1800}
        show(host, plan, token)
    except RepairError as exc:
        host.say('⛔ ' + host.esc(str(exc)))


def show(host, plan, token):
    lines = ['🧹 <b>이전 변경·충돌 정리</b>',
             '브랜치: <code>' + host.esc(plan['branch']) + '</code>',
             '충돌: ' + host.esc(', '.join(plan['conflicts']) or '없음'),
             '이미 처리돼 이번 업데이트에서 제외할 파일을 선택하세요.',
             '선택 파일은 main 상태로 복원되며 main에서 삭제된 파일은 삭제 상태로 맞춥니다.',
             '선택하지 않은 수정은 보존합니다.']
    rows = []
    for index, path in enumerate(plan['paths']):
        mark = '☑️' if path in plan['selected'] else '⬜'
        rows.append([{'text': mark + ' ' + path,
                      'callback_data': 'ct:' + token + ':' + str(index)}])
    rows += [[{'text': '✅ 선택한 이전 변경 정리 확인', 'callback_data': 'cc:' + token}],
             [{'text': '취소', 'callback_data': 'cx:' + token}]]
    host.say('\n'.join(lines), rows)


def handle(host, state, action, key):
    token, _, index = key.partition(':')
    plan = state.get('conflict_plans', {}).get(token)
    if not plan or time.time() - plan.get('at', 0) >= 1800:
        return host.say('⚠️ 정리 화면이 만료됐습니다. 최신 알림에서 다시 열어 주세요.')
    if action == 'cx':
        state['conflict_plans'].pop(token, None)
        return host.say('정리를 취소했습니다. 브랜치는 변경하지 않았습니다.')
    if action == 'ct':
        if not index.isdigit() or int(index) >= len(plan['paths']):
            return host.say('⚠️ 파일 선택 정보가 잘못됐습니다.')
        path = plan['paths'][int(index)]
        if path in plan['selected']:
            plan['selected'].remove(path)
        else:
            plan['selected'].append(path)
        plan.pop('reviewed', None)
        return show(host, plan, token)
    if action == 'cc':
        if not plan['selected']:
            return host.say('⚠️ 이번 업데이트에서 제외할 이전 변경 파일을 먼저 선택하세요.')
        plan['reviewed'] = sorted(plan['selected'])
        return host.say('다음 파일의 이전 변경을 제외하고 원래 브랜치를 정리합니다.\n'
                        + host.esc('\n'.join(plan['reviewed']))
                        + '\n정리 전 브랜치를 백업합니다. 거래봇 적용·재시작은 하지 않습니다.',
                        [[{'text': '🧹 백업 후 정리 실행', 'callback_data': 'cr:' + token}],
                         [{'text': '취소', 'callback_data': 'cx:' + token}]])
    if action != 'cr':
        return
    if plan.get('reviewed') != sorted(plan['selected']):
        return host.say('⚠️ 선택 내용을 먼저 확인해 주세요.')
    try:
        snapshot(host, plan['branch'], plan['sha'], plan['main'])
        result = build(host, plan, plan['selected'], publish=True)
    except RepairError as exc:
        return host.say('⛔ ' + host.esc(str(exc)) + '\n서버 운영 코드는 변경하지 않았습니다.')
    state['conflict_plans'].pop(token, None)
    state.get('offers', {}).pop(plan['offer_key'], None)
    state.setdefault('seen', {}).pop(plan['branch'], None)
    host.say('✅ 같은 브랜치의 충돌·이전 변경 정리 완료\n백업 태그: <code>'
             + host.esc(result['backup']) + '</code>\n남은 수정: '
             + host.esc(', '.join(result['files']) or '없음')
             + '\n새 업데이트 알림을 확인하고 별도로 승인하세요.')
    host.scan(state, force=True)


def cli():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', required=True)
    parser.add_argument('--branch', default='staging')
    parser.add_argument('--discard', nargs='*', default=[])
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--expected', help='미리 확인한 업데이트 브랜치 전체 SHA')
    args = parser.parse_args()
    def git(*values):
        result = subprocess.run(['git', '-C', args.repo, *values], capture_output=True,
                                text=True, env={**os.environ, 'GIT_TERMINAL_PROMPT': '0'}, timeout=120)
        return result.returncode, result.stdout.rstrip('\n')
    host = SimpleNamespace(git=git)
    try:
        if args.apply and not args.expected:
            raise RepairError('--apply에는 미리 확인한 SHA를 --expected로 지정해야 합니다.')
        plan = snapshot(host, args.branch, args.expected)
        if args.apply and not args.discard:
            raise RepairError('--apply에는 제외할 파일을 --discard로 명시해야 합니다.')
        result = build(host, plan, args.discard, publish=args.apply)
        print(json.dumps({'branch': args.branch, 'source_sha': plan['sha'], 'main_sha': plan['main'],
                          'changed_files': plan['paths'], 'applied': args.apply, **result}, ensure_ascii=False, indent=2))
    except (RepairError, subprocess.TimeoutExpired) as exc:
        parser.exit(1, str(exc) + '\n')


if __name__ == '__main__':
    cli()
