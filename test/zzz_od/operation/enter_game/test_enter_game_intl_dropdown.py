"""EnterGame 国际服历史账号下拉切换测试（issue #2756）。

覆盖国际服在登录界面通过"历史账号下拉菜单"选择已登录账号登录（避免输入密码触发验证码）：

- ``check_screen_intl`` 在账号确认态 + 配置了 ``intl_account_name`` 时返回 ``国际服-账号确认``；
- 未配置 ``intl_account_name`` 时不触发下拉切换（保持原有输密码流程）；
- ``switch_intl_account_by_dropdown`` 完整下拉切换：点展开(▽)→选号→(必要时)收起(△)→点进入游戏。

存档截图用测试仓 ``screens/打开游戏/`` 的国服账号确认态（miHoYo UI，结构与国际服一致，
坐标已按同一套 screen_info 建模）。``intl_account_name`` 填存档里掩码账号 ``135*****95``。
"""

from __future__ import annotations

import pytest
from test.conftest import TestContext
from test.harness.fixture_controller import FixtureController

from zzz_od.operation.enter_game.enter_game import EnterGame


class TestCheckScreenIntl:

    def test_check_screen_intl_detects_account_confirm(
        self,
        test_context: TestContext,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """国际服 + 配置 intl_account_name + 账号确认态(收起) → 返回 国际服-账号确认。"""
        monkeypatch.setattr(test_context.game_account_config, 'game_region', 'us')
        monkeypatch.setattr(test_context.game_account_config, 'intl_account_name', '135*****95')

        op = EnterGame(test_context, switch=False)
        screen = test_context.load_screen('打开游戏', '账号确认')
        result = op.check_screen_intl(screen)

        assert result is not None
        assert result.is_success
        assert result.status == '国际服-账号确认'

    def test_check_screen_intl_returns_none_without_name(
        self,
        test_context: TestContext,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """国际服 + 未配置 intl_account_name → 不触发下拉切换（保持原有流程）。"""
        monkeypatch.setattr(test_context.game_account_config, 'game_region', 'us')
        monkeypatch.setattr(test_context.game_account_config, 'intl_account_name', '')

        op = EnterGame(test_context, switch=False)
        screen = test_context.load_screen('打开游戏', '账号确认')
        result = op.check_screen_intl(screen)

        assert result is None


class TestSwitchIntlAccountByDropdown:

    @pytest.fixture()
    def fixture_controller(
        self,
        test_context: TestContext,
        monkeypatch: pytest.MonkeyPatch,
    ) -> FixtureController:
        """注入 FixtureController，记录点击并用存档帧推进。"""
        ctrl = FixtureController(
            ctx=test_context,
            standard_width=test_context.project_config.screen_standard_width,
            standard_height=test_context.project_config.screen_standard_height,
        )
        monkeypatch.setattr(test_context, 'controller', ctrl)
        monkeypatch.setattr(test_context.game_account_config, 'game_region', 'us')
        monkeypatch.setattr(test_context.game_account_config, 'intl_account_name', '135*****95')
        return ctrl

    def _build_phases(self) -> list[dict]:
        """下拉切换剧本。

        - phase0: 展开态(账号确认-下拉) → 点开历史账号列表里的目标账号(click 落列表区域);
        - phase1: 展开态 → 点收起(△) 露出"进入游戏"按钮;
        - phase2: 收起态(账号确认) → 点"进入游戏";
        - phase3: 选区服(terminal)。
        """
        return [
            {
                'frame': ('打开游戏', '账号确认-下拉'),
                'exit': ('on_click_in', '打开游戏', '国际服-历史账号列表'),
            },
            {
                'frame': ('打开游戏', '账号确认-下拉'),
                'exit': ('on_click_in', '打开游戏', '账号下拉-点击收起'),
            },
            {
                'frame': ('打开游戏', '账号确认'),
                'exit': ('on_click_in', '打开游戏', '账号确认-进入游戏'),
            },
            {
                'frame': ('打开游戏', '选区服'),
            },
        ]

    def test_switch_intl_account_by_dropdown(
        self,
        test_context: TestContext,
        fixture_controller: FixtureController,
    ) -> None:
        fixture_controller.set_phases(self._build_phases())

        op = EnterGame(test_context, switch=False)
        op.last_screenshot = fixture_controller.current_frame

        result = op.switch_intl_account_by_dropdown()

        # 节点成功返回"进入游戏"点击结果
        assert result.is_success
        assert result.status == '账号确认-进入游戏'

        # 剧本推进到末 phase
        assert fixture_controller.phase_idx == len(self._build_phases()) - 1, (
            f'剧本未推进到末 phase：phase_idx={fixture_controller.phase_idx}'
        )

        # 关键流程 click 被记录：选号点击(列表区域) + 进入游戏点击
        assert fixture_controller.click_hit_area('打开游戏', '国际服-历史账号列表'), (
            '未记录到历史账号列表选号 click：'
            f'{_fmt_clicks(fixture_controller.recorded_clicks)}'
        )
        assert fixture_controller.click_hit_area('打开游戏', '账号确认-进入游戏'), (
            '未记录到"进入游戏" click：'
            f'{_fmt_clicks(fixture_controller.recorded_clicks)}'
        )

    def test_switch_intl_account_by_dropdown_no_name_fails(
        self,
        test_context: TestContext,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """未配置 intl_account_name → 节点直接失败，不进行任何点击。"""
        ctrl = FixtureController(
            ctx=test_context,
            standard_width=test_context.project_config.screen_standard_width,
            standard_height=test_context.project_config.screen_standard_height,
        )
        monkeypatch.setattr(test_context, 'controller', ctrl)
        monkeypatch.setattr(test_context.game_account_config, 'intl_account_name', '')
        ctrl.set_phases(
            [
                {'frame': ('打开游戏', '账号确认-下拉')},
            ]
        )

        op = EnterGame(test_context, switch=False)
        op.last_screenshot = ctrl.current_frame

        result = op.switch_intl_account_by_dropdown()

        assert not result.is_success
        assert ctrl.recorded_clicks == [], '未配置账号名时不应进行任何点击'


def _fmt_clicks(clicks: list) -> str:
    return ', '.join(f'({p.x},{p.y})' for p in clicks) or '<empty>'
