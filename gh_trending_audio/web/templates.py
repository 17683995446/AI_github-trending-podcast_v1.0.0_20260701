"""HTML templates for the web dashboard.

These two string constants are filled via str.format() in the handler.
They are extracted verbatim from the original web_dashboard.py and must
not be reformatted (the doubled braces {{ }} are intentional).
"""

DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>GitHub Trending Audio</title>
    <style>
        /* ═══ 多主题系统 ═══ */
        :root {{
            --radius: 12px;
            --transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
        }}
        /* ── Dark（默认） ── */
        [data-theme="dark"] {{
            --bg: #0d1117; --bg-gradient: radial-gradient(ellipse at top, #161b22 0%, #0d1117 60%);
            --card-bg: #161b22; --card-hover: #1c2330;
            --border: #30363d; --border-light: #21262d;
            --text: #e6edf3; --text-dim: #8b949e;
            --accent: #58a6ff; --accent-glow: rgba(88,166,255,0.15);
            --green: #3fb950; --red: #f85149; --yellow: #d29922; --purple: #bc8cff;
            --tab-active: #1f6feb; --hover-bg: #1c2128;
            --shadow-sm: 0 2px 8px rgba(0,0,0,0.2); --shadow-md: 0 4px 16px rgba(0,0,0,0.3); --shadow-lg: 0 8px 32px rgba(0,0,0,0.4);
            --header-bg: rgba(22,27,34,0.85); --glass-blur: blur(12px);
        }}
        /* ── Light ── */
        [data-theme="light"] {{
            --bg: #f6f8fa; --bg-gradient: radial-gradient(ellipse at top, #ffffff 0%, #f6f8fa 60%);
            --card-bg: #ffffff; --card-hover: #f0f3f6;
            --border: #d0d7de; --border-light: #eaeef2;
            --text: #1f2328; --text-dim: #656d76;
            --accent: #0969da; --accent-glow: rgba(9,105,218,0.12);
            --green: #1a7f37; --red: #cf222e; --yellow: #9a6700; --purple: #8250df;
            --tab-active: #0969da; --hover-bg: #eaeef2;
            --shadow-sm: 0 2px 8px rgba(0,0,0,0.06); --shadow-md: 0 4px 16px rgba(0,0,0,0.1); --shadow-lg: 0 8px 32px rgba(0,0,0,0.12);
            --header-bg: rgba(255,255,255,0.85); --glass-blur: blur(12px);
        }}
        /* ── Midnight（深蓝紫） ── */
        [data-theme="midnight"] {{
            --bg: #0f0f23; --bg-gradient: radial-gradient(ellipse at top, #1a1a3e 0%, #0f0f23 60%);
            --card-bg: #1a1a3e; --card-hover: #252550;
            --border: #3a3a6e; --border-light: #2a2a52;
            --text: #e0e0ff; --text-dim: #8888bb;
            --accent: #7c7cff; --accent-glow: rgba(124,124,255,0.18);
            --green: #50e3a0; --red: #ff6b8a; --yellow: #ffd966; --purple: #c084fc;
            --tab-active: #7c7cff; --hover-bg: #252550;
            --shadow-sm: 0 2px 8px rgba(0,0,0,0.3); --shadow-md: 0 4px 16px rgba(0,0,0,0.4); --shadow-lg: 0 8px 32px rgba(0,0,0,0.5);
            --header-bg: rgba(26,26,62,0.85); --glass-blur: blur(12px);
        }}
        /* ── Nord ── */
        [data-theme="nord"] {{
            --bg: #2e3440; --bg-gradient: radial-gradient(ellipse at top, #3b4252 0%, #2e3440 60%);
            --card-bg: #3b4252; --card-hover: #434c5e;
            --border: #4c566a; --border-light: #3f485a;
            --text: #eceff4; --text-dim: #81a1c1;
            --accent: #88c0d0; --accent-glow: rgba(136,192,208,0.15);
            --green: #a3be8c; --red: #bf616a; --yellow: #ebcb8b; --purple: #b48ead;
            --tab-active: #88c0d0; --hover-bg: #434c5e;
            --shadow-sm: 0 2px 8px rgba(0,0,0,0.25); --shadow-md: 0 4px 16px rgba(0,0,0,0.35); --shadow-lg: 0 8px 32px rgba(0,0,0,0.45);
            --header-bg: rgba(59,66,82,0.85); --glass-blur: blur(12px);
        }}
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, 'Segoe UI', 'Noto Sans CJK SC', sans-serif;
            background: var(--bg-gradient); color: var(--text);
            min-height: 100vh; padding-bottom: 70px;
        }}
        /* ── 主题切换器 ── */
        .theme-switcher {{
            display: flex; gap: 6px; align-items: center;
            padding: 4px 8px; border-radius: 20px;
            background: var(--card-bg); border: 1px solid var(--border-light);
        }}
        .theme-dot {{
            width: 18px; height: 18px; border-radius: 50%;
            border: 2px solid var(--border); cursor: pointer;
            transition: transform 0.2s, box-shadow 0.2s; padding: 0;
        }}
        .theme-dot:hover {{ transform: scale(1.2); }}
        .theme-dot.active {{
            transform: scale(1.25);
            box-shadow: 0 0 0 2px var(--accent), 0 0 8px var(--accent-glow);
        }}

        /* ── 顶部 ── */
        .header {{
            background: var(--header-bg); backdrop-filter: var(--glass-blur);
            border-bottom: 1px solid var(--border);
            padding: 14px 32px; display: flex; align-items: center;
            justify-content: space-between; flex-wrap: wrap; gap: 12px;
            position: sticky; top: 0; z-index: 100;
        }}
        .header h1 {{
            font-size: 21px; background: linear-gradient(135deg, var(--accent), var(--purple));
            -webkit-background-clip: text; -webkit-text-fill-color: transparent;
            background-clip: text;
        }}

        /* ── 标签页 ── */
        .tab-nav {{
            display: flex; background: var(--header-bg); backdrop-filter: var(--glass-blur);
            border-bottom: 1px solid var(--border); padding: 0 32px;
            position: sticky; top: 60px; z-index: 99;
        }}
        .tab-btn {{
            padding: 12px 24px; background: none; border: none;
            color: var(--text-dim); font-size: 14px; cursor: pointer;
            border-bottom: 2px solid transparent; transition: var(--transition);
            position: relative;
        }}
        .tab-btn:hover {{ color: var(--text); }}
        .tab-btn.active {{ color: var(--accent); border-bottom-color: var(--tab-active); }}
        .tab-btn.active::after {{
            content: ''; position: absolute; bottom: -1px; left: 0; right: 0;
            height: 2px; background: linear-gradient(90deg, var(--accent), var(--purple));
        }}
        .tab-badge {{
            display: inline-block; background: var(--border); color: var(--text-dim);
            border-radius: 10px; padding: 1px 8px; font-size: 12px; margin-left: 6px;
        }}
        .tab-btn.active .tab-badge {{ background: var(--accent); color: #fff; }}

        .tab-content {{ display: none; padding: 24px 32px; max-width: 1400px; margin: 0 auto; }}
        .tab-content.active {{ display: block; animation: fadeIn 0.3s ease; }}
        @keyframes fadeIn {{ from {{ opacity: 0; transform: translateY(8px); }} to {{ opacity: 1; transform: translateY(0); }} }}

        /* ── 工具栏 ── */
        .toolbar {{
            display: flex; gap: 10px; flex-wrap: wrap; align-items: center;
            margin-bottom: 20px;
        }}
        .search-box {{
            flex: 1; min-width: 200px;
            background: var(--card-bg); border: 1px solid var(--border-light);
            color: var(--text); border-radius: var(--radius); padding: 10px 16px;
            font-size: 14px; transition: var(--transition);
        }}
        .search-box:focus {{ outline: none; border-color: var(--accent); box-shadow: 0 0 0 3px var(--accent-glow); }}
        .toolbar select {{
            background: var(--card-bg); border: 1px solid var(--border-light);
            color: var(--text); border-radius: var(--radius); padding: 10px 12px;
            font-size: 14px; cursor: pointer; transition: var(--transition);
        }}
        .toolbar select:focus {{ outline: none; border-color: var(--accent); box-shadow: 0 0 0 3px var(--accent-glow); }}

        /* ── 统计卡片 ── */
        .stats-grid {{
            display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
            gap: 14px; margin-bottom: 24px;
        }}
        .stat-card {{
            background: var(--card-bg); border: 1px solid var(--border-light);
            border-radius: var(--radius); padding: 16px 20px;
            transition: var(--transition); position: relative; overflow: hidden;
            display: flex; align-items: center; gap: 14px;
        }}
        .stat-card::before {{
            content: ''; position: absolute; top: 0; left: 0; right: 0; height: 2px;
            background: linear-gradient(90deg, var(--accent), var(--purple));
            opacity: 0; transition: opacity 0.25s;
        }}
        .stat-card:hover {{ border-color: var(--accent); transform: translateY(-3px); box-shadow: var(--shadow-md); }}
        .stat-card:hover::before {{ opacity: 1; }}
        .stat-icon {{
            font-size: 28px; line-height: 1;
            filter: drop-shadow(0 2px 4px rgba(0,0,0,0.2));
        }}
        .stat-body .number {{ font-size: 24px; font-weight: 700; color: var(--accent); }}
        .stat-body .label {{ font-size: 12px; color: var(--text-dim); margin-top: 2px; }}

        /* ── 项目卡片 ── */
        .projects-grid {{
            display: grid; grid-template-columns: repeat(auto-fill, minmax(380px, 1fr));
            gap: 16px;
        }}
        .project-card {{
            background: var(--card-bg); border: 1px solid var(--border-light);
            border-radius: var(--radius); padding: 18px; cursor: pointer;
            transition: var(--transition); position: relative; overflow: hidden;
        }}
        .project-card::before {{
            content: ''; position: absolute; top: 0; left: 0; right: 0; height: 3px;
            background: linear-gradient(90deg, var(--accent), var(--purple));
            transform: scaleX(0); transform-origin: left; transition: transform 0.3s;
        }}
        .project-card:hover {{
            border-color: var(--accent); transform: translateY(-3px);
            box-shadow: var(--shadow-md); background: var(--card-hover);
        }}
        .project-card:hover::before {{ transform: scaleX(1); }}
        .project-card.selected {{ border-color: var(--green); background: rgba(63,185,80,0.05); }}
        .project-card.selected::before {{ background: linear-gradient(90deg, var(--green), var(--accent)); transform: scaleX(1); }}
        .card-checkbox {{
            position: absolute; top: 14px; right: 14px;
            width: 18px; height: 18px; cursor: pointer; accent-color: var(--green);
        }}
        .card-title {{
            font-size: 15px; font-weight: 600; padding-right: 28px;
            overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
        }}
        .card-desc {{
            font-size: 13px; color: var(--text-dim); margin-top: 6px;
            overflow: hidden; text-overflow: ellipsis; display: -webkit-box;
            -webkit-line-clamp: 2; -webkit-box-orient: vertical; line-height: 1.4;
            min-height: 36px;
        }}
        .card-tags {{ display: flex; gap: 6px; flex-wrap: wrap; margin-top: 8px; }}
        .tag {{
            font-size: 11px; padding: 2px 8px; border-radius: 10px;
            background: rgba(88,166,255,0.1); color: var(--accent);
        }}
        .tag.lang {{ background: rgba(63,185,80,0.1); color: var(--green); }}
        .tag.stars {{ background: rgba(210,153,34,0.1); color: var(--yellow); }}
        .tag.duration {{ background: rgba(163,113,247,0.1); color: #a371f7; }}
        .card-footer {{
            display: flex; justify-content: space-between; align-items: center;
            margin-top: 10px;
        }}
        .card-size {{ font-size: 12px; color: var(--text-dim); }}
        .card-actions {{ display: flex; gap: 6px; }}
        .card-btn {{
            background: var(--bg); border: 1px solid var(--border-light); color: var(--text);
            border-radius: 6px; padding: 4px 10px; font-size: 13px;
            cursor: pointer; transition: all 0.2s; text-decoration: none;
            display: inline-flex; align-items: center; gap: 4px;
        }}
        .card-btn:hover {{ border-color: var(--accent); box-shadow: 0 0 0 2px var(--accent-glow); }}
        .play-btn {{ background: rgba(63,185,80,0.1); border-color: rgba(63,185,80,0.3); color: var(--green); }}
        .play-btn:hover {{ color: var(--green); border-color: var(--green); box-shadow: 0 0 0 2px rgba(63,185,80,0.15); }}
        .delete-btn:hover {{ color: var(--red); border-color: var(--red); box-shadow: 0 0 0 2px rgba(248,81,73,0.15); }}

        /* ── 表单 ── */
        .form-row {{ display: flex; gap: 12px; flex-wrap: wrap; align-items: flex-end; }}
        .form-group {{ display: flex; flex-direction: column; gap: 4px; }}
        .form-group label {{ font-size: 12px; color: var(--text-dim); }}
        .form-group input, .form-group select {{
            background: var(--bg); border: 1px solid var(--border); color: var(--text);
            border-radius: 6px; padding: 8px 12px; font-size: 14px; width: 120px;
        }}
        .btn {{
            background: linear-gradient(135deg, var(--accent), #4a90e2); color: #fff; border: none;
            border-radius: var(--radius); padding: 10px 22px; font-size: 14px; cursor: pointer;
            transition: var(--transition); box-shadow: 0 2px 8px rgba(88,166,255,0.25);
        }}
        .btn:hover {{ transform: translateY(-1px); box-shadow: 0 4px 16px rgba(88,166,255,0.35); }}
        .btn:active {{ transform: translateY(0); }}
        .btn:disabled {{ opacity: 0.5; cursor: not-allowed; transform: none; }}
        .btn-danger {{ background: linear-gradient(135deg, var(--red), #da3633); box-shadow: 0 2px 8px rgba(248,81,73,0.25); }}
        .btn-secondary {{
            background: var(--card-bg); border: 1px solid var(--border-light); color: var(--text);
            box-shadow: none;
        }}
        .btn-secondary:hover {{ border-color: var(--accent); box-shadow: 0 0 0 3px var(--accent-glow); transform: none; }}

        .status-bar {{
            margin-top: 12px; padding: 10px 16px; border-radius: 8px;
            font-size: 14px; display: none;
        }}
        .status-bar.running {{ background: rgba(88,166,255,0.1); color: var(--accent); display: block; }}
        .status-bar.success {{ background: rgba(63,185,80,0.1); color: var(--green); display: block; }}
        .status-bar.error {{ background: rgba(248,81,73,0.1); color: var(--red); display: block; }}

        .badge {{ padding: 2px 8px; border-radius: 10px; font-size: 11px; font-weight: 600; }}
        .badge-success {{ background: rgba(63,185,80,0.15); color: var(--green); }}
        .badge-warning {{ background: rgba(210,153,34,0.15); color: var(--yellow); }}

        /* ── 播放列表 ── */
        .playlist-item {{
            display: flex; align-items: center; gap: 12px; padding: 10px 16px;
            background: var(--card-bg); border: 1px solid var(--border);
            border-radius: 8px; margin-bottom: 8px; cursor: pointer; transition: border-color 0.2s;
        }}
        .playlist-item:hover {{ border-color: var(--accent); }}
        .playlist-item.playing {{ border-color: var(--green); background: rgba(63,185,80,0.05); }}
        .playlist-item .idx {{ color: var(--text-dim); font-size: 14px; width: 24px; }}
        .playlist-item .name {{ flex: 1; font-size: 14px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }}
        .playlist-item .play-icon {{ color: var(--accent); }}

        .empty {{ text-align: center; padding: 60px; color: var(--text-dim); }}
        .spinner {{
            display: inline-block; width: 16px; height: 16px;
            border: 2px solid var(--text-dim); border-top-color: var(--accent);
            border-radius: 50%; animation: spin 0.8s linear infinite; margin-right: 8px;
        }}
        @keyframes spin {{ to {{ transform: rotate(360deg); }} }}

        /* ── 浮动播放器 ── */
        .player-bar {{
            position: fixed; bottom: 0; left: 0; right: 0;
            background: var(--card-bg);
            border-top: 1px solid var(--border);
            padding: 10px 24px; display: flex; align-items: center; gap: 12px;
            z-index: 10000; box-shadow: 0 -8px 24px rgba(0,0,0,0.4);
        }}
        .player-bar.hidden {{ display: none; }}
        .player-bar .track-info {{ display: flex; flex-direction: column; min-width: 180px; max-width: 280px; }}
        .player-bar .track-name {{
            font-size: 13px; font-weight: 600;
            overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
        }}
        .player-bar .track-status {{ font-size: 11px; color: var(--text-dim); }}
        .player-bar audio {{ flex: 1; height: 36px; }}
        .speed-select {{
            background: var(--bg); border: 1px solid var(--border-light); color: var(--text);
            border-radius: 6px; padding: 4px 8px; font-size: 12px; cursor: pointer;
            transition: all 0.2s;
        }}
        .speed-select:hover {{ border-color: var(--accent); }}
        .player-download {{
            background: var(--bg); border: 1px solid var(--border-light); color: var(--text);
            border-radius: 6px; padding: 4px 10px; font-size: 13px;
            cursor: pointer; text-decoration: none; display: inline-flex; align-items: center;
        }}
        .player-download:hover {{ border-color: var(--accent); color: var(--accent); }}
        .player-close {{
            background: none; border: none; color: var(--text-dim);
            font-size: 18px; cursor: pointer; padding: 4px;
        }}
        .player-close:hover {{ color: var(--red); }}

        /* ── 底部导航栏 ── */
        .bottom-nav {{
            position: fixed; bottom: 0; left: 0; right: 0;
            background: var(--card-bg);
            border-top: 1px solid var(--border);
            display: flex; justify-content: center; gap: 8px;
            padding: 8px 16px; z-index: 9999;
            box-shadow: 0 -4px 24px rgba(0,0,0,0.4);
        }}
        .bottom-nav-item {{
            display: flex; flex-direction: column; align-items: center; gap: 2px;
            background: none; border: none; color: var(--text-dim);
            font-size: 11px; cursor: pointer; padding: 6px 16px;
            border-radius: 10px; transition: var(--transition);
            text-decoration: none; min-width: 64px;
        }}
        .bottom-nav-item svg {{ width: 22px; height: 22px; }}
        .bottom-nav-item:hover {{ color: var(--text); background: var(--hover-bg); }}
        .bottom-nav-item.active {{
            color: var(--accent); background: var(--accent-glow);
        }}
        /* 当 player-bar 显示时，底部导航栏上移避免遮挡 */
        .bottom-nav.with-player {{ bottom: 56px; }}
        /* ── 流程图 / 架构图 ── */
        .flow-section {{
            background: var(--card-bg); border: 1px solid var(--border);
            border-radius: var(--radius); padding: 24px; margin: 0 32px 20px;
            max-width: 1336px;
        }}
        .flow-title {{
            font-size: 16px; font-weight: 700; margin-bottom: 4px;
            display: flex; align-items: center; gap: 8px;
        }}
        .flow-desc {{ color: var(--text-dim); font-size: 13px; margin-bottom: 20px; }}
        .flow-chart {{
            display: flex; align-items: stretch; gap: 0; flex-wrap: wrap;
            justify-content: center;
        }}
        .flow-step {{
            display: flex; flex-direction: column; align-items: center;
            gap: 6px; min-width: 120px; max-width: 150px; flex: 1;
            position: relative;
        }}
        .flow-step-icon {{
            width: 56px; height: 56px; border-radius: 50%;
            display: flex; align-items: center; justify-content: center;
            font-size: 26px; position: relative; z-index: 2;
            border: 2px solid var(--border);
        }}
        .flow-step:nth-child(1) .flow-step-icon {{ background: var(--accent-glow); border-color: var(--accent); }}
        .flow-step:nth-child(3) .flow-step-icon {{ background: rgba(63,185,80,0.12); border-color: var(--green); }}
        .flow-step:nth-child(5) .flow-step-icon {{ background: rgba(210,153,34,0.12); border-color: var(--yellow); }}
        .flow-step:nth-child(7) .flow-step-icon {{ background: rgba(188,140,255,0.12); border-color: var(--purple); }}
        .flow-step:nth-child(9) .flow-step-icon {{ background: var(--accent-glow); border-color: var(--accent); }}
        .flow-step:nth-child(11) .flow-step-icon {{ background: rgba(63,185,80,0.12); border-color: var(--green); }}
        .flow-step-name {{ font-size: 13px; font-weight: 600; text-align: center; }}
        .flow-step-detail {{ font-size: 11px; color: var(--text-dim); text-align: center; line-height: 1.4; }}
        .flow-arrow {{
            display: flex; align-items: center; color: var(--text-dim);
            font-size: 20px; padding: 0 2px; align-self: center; margin-top: -20px;
        }}
        /* 架构图 */
        .arch-diagram {{
            display: flex; flex-direction: column; gap: 12px; align-items: center;
        }}
        .arch-layer {{
            display: flex; gap: 12px; justify-content: center; flex-wrap: wrap;
            width: 100%;
        }}
        .arch-layer-label {{
            font-size: 11px; color: var(--text-dim); font-weight: 600;
            text-transform: uppercase; letter-spacing: 1px; margin-bottom: 2px;
            text-align: center; width: 100%;
        }}
        .arch-box {{
            background: var(--bg); border: 1px solid var(--border);
            border-radius: 10px; padding: 10px 16px; text-align: center;
            min-width: 100px; transition: var(--transition);
        }}
        .arch-box:hover {{ border-color: var(--accent); transform: translateY(-2px); }}
        .arch-box-icon {{ font-size: 22px; }}
        .arch-box-name {{ font-size: 12px; font-weight: 600; margin-top: 4px; }}
        .arch-box-tag {{ font-size: 10px; color: var(--text-dim); }}
        .arch-connector {{
            width: 2px; height: 16px; background: var(--border);
        }}
        .arch-box.accent {{ border-color: var(--accent); background: var(--accent-glow); }}
        .arch-box.green {{ border-color: var(--green); background: rgba(63,185,80,0.08); }}
        .arch-box.purple {{ border-color: var(--purple); background: rgba(188,140,255,0.08); }}

        /* ── 批量操作栏 ── */
        .batch-bar {{
            display: none; position: fixed; top: 80px; right: 32px;
            background: var(--card-bg); border: 1px solid var(--border);
            border-radius: 10px; padding: 12px 16px; gap: 8px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.4); z-index: 150;
            align-items: center;
        }}
        .batch-bar.visible {{ display: flex; }}
        .batch-bar .batch-count {{ font-size: 13px; color: var(--accent); margin-right: 8px; }}

        /* ── 快速分析输入框（搜索栏旁）── */
        .quick-input {{
            flex: 1.2; min-width: 260px;
            background: var(--card-bg); border: 1px solid var(--border);
            color: var(--text); border-radius: 8px; padding: 10px 16px; font-size: 14px;
        }}
        .quick-input:focus {{ outline: none; border-color: var(--accent); }}
        .quick-input::placeholder {{ color: var(--text-dim); }}
        .quick-btn {{ padding: 10px 18px; flex-shrink: 0; }}

        /* ── Header 右侧 + 书签按钮 ── */
        .header-right {{ display: flex; align-items: center; gap: 14px; flex-wrap: wrap; }}
        .header-sub {{ color: var(--text-dim); font-size: 13px; }}
        .bookmark-btn {{ font-size: 13px; padding: 7px 14px; white-space: nowrap; }}

        /* ── 书签说明弹窗 ── */
        .modal-overlay {{
            display: none; position: fixed; inset: 0;
            background: rgba(0,0,0,0.65); z-index: 300;
            align-items: center; justify-content: center; padding: 24px;
        }}
        .modal-overlay.visible {{ display: flex; }}
        .modal-box {{
            background: var(--card-bg); border: 1px solid var(--border);
            border-radius: 12px; padding: 26px 28px; max-width: 660px; width: 100%;
            position: relative; box-shadow: 0 8px 32px rgba(0,0,0,0.5);
            max-height: 90vh; overflow-y: auto;
        }}
        .modal-close {{
            position: absolute; top: 12px; right: 14px; background: none;
            border: none; color: var(--text-dim); font-size: 18px; cursor: pointer;
        }}
        .modal-close:hover {{ color: var(--red); }}
        .modal-box h3 {{ font-size: 17px; margin-bottom: 10px; color: var(--accent); }}
        .modal-desc {{ font-size: 13px; color: var(--text-dim); line-height: 1.6; margin-bottom: 16px; }}
        .bookmarklet-row {{
            display: flex; align-items: center; gap: 14px; margin-bottom: 18px; flex-wrap: wrap;
            background: var(--bg); border: 1px dashed var(--border);
            border-radius: 10px; padding: 16px;
        }}
        .bookmarklet-link {{
            display: inline-block; background: var(--accent); color: #fff;
            padding: 10px 20px; border-radius: 8px; text-decoration: none;
            font-size: 14px; font-weight: 600; cursor: grab; white-space: nowrap;
        }}
        .bookmarklet-link:hover {{ opacity: 0.88; color: #fff; }}
        .bookmarklet-hint {{ color: var(--text-dim); font-size: 12px; }}
        .copy-btn {{
            background: var(--card-bg); border: 1px solid var(--border); color: var(--text);
            border-radius: 6px; padding: 6px 12px; font-size: 12px; cursor: pointer;
        }}
        .copy-btn:hover {{ border-color: var(--accent); color: var(--accent); }}
        .modal-section {{ margin-top: 16px; }}
        .modal-label {{ font-size: 12px; color: var(--text-dim); margin-bottom: 6px; }}
        .code-block {{
            background: var(--bg); border: 1px solid var(--border); border-radius: 8px;
            padding: 12px; font-size: 12px; color: var(--green); white-space: pre-wrap;
            word-break: break-all; max-height: 120px; overflow: auto;
            font-family: 'SFMono-Regular', Consolas, monospace;
        }}
        .code-inline {{
            display: inline-block; background: var(--bg); border: 1px solid var(--border);
            border-radius: 6px; padding: 6px 12px; font-size: 13px; color: var(--accent);
            font-family: 'SFMono-Regular', Consolas, monospace;
        }}
        .modal-tip {{ font-size: 12px; color: var(--text-dim); margin-top: 8px; line-height: 1.6; }}
        .modal-tip code {{ background: var(--bg); padding: 1px 6px; border-radius: 4px; color: var(--accent); }}
    </style>
</head>
<body data-theme="dark">
    <!-- 主题初始化（必须在 CSS 之后、内容之前执行，避免闪烁） -->
    <script>
        (function() {{
            var t = localStorage.getItem('gh-audio-theme') || 'dark';
            document.body.setAttribute('data-theme', t);
        }})();
    </script>
    <div class="header">
        <h1>🎙️ GitHub Trending Audio</h1>
        <div class="header-right">
            <span class="header-sub">自动获取 GitHub 趋势项目 → 双人对话播客</span>
            <div class="theme-switcher" id="themeSwitcher">
                <button class="theme-dot" data-theme="dark" style="background:#0d1117;border-color:#58a6ff" title="Dark"></button>
                <button class="theme-dot" data-theme="light" style="background:#f6f8fa;border-color:#0969da" title="Light"></button>
                <button class="theme-dot" data-theme="midnight" style="background:#0f0f23;border-color:#7c7cff" title="Midnight"></button>
                <button class="theme-dot" data-theme="nord" style="background:#2e3440;border-color:#88c0d0" title="Nord"></button>
            </div>
            <button class="btn btn-secondary" onclick="openPlayer()">🎧 播放器</button>
            <button class="btn btn-secondary bookmark-btn" onclick="showBookmarkModal()">🔖 添加书签</button>
        </div>
    </div>

    <div class="tab-nav">
        <button class="tab-btn active" onclick="switchTab('projects')" id="tab-projects">
            📁 项目列表 <span class="tab-badge" id="badge-projects">0</span>
        </button>
        <button class="tab-btn" onclick="switchTab('generate')" id="tab-generate">🚀 生成任务</button>
    </div>

    <!-- Tab 1: 项目列表 -->
    <div class="tab-content active" id="content-projects">
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-icon">📁</div>
                <div class="stat-body">
                    <div class="number">{total_projects}</div>
                    <div class="label">总项目</div>
                </div>
            </div>
            <div class="stat-card">
                <div class="stat-icon">🎵</div>
                <div class="stat-body">
                    <div class="number">{total_audio}</div>
                    <div class="label">音频数</div>
                </div>
            </div>
            <div class="stat-card">
                <div class="stat-icon">⏱️</div>
                <div class="stat-body">
                    <div class="number" id="stat-duration">—</div>
                    <div class="label">总时长</div>
                </div>
            </div>
        </div>

        <!-- 系统架构图 -->
        <div class="flow-section">
            <div class="flow-title">🏗️ 系统架构</div>
            <div class="flow-desc">从 GitHub 趋势项目到双人对话播客，四层架构自动完成全流程</div>
            <div class="arch-diagram">
                <!-- 第一层：数据采集 -->
                <div class="arch-layer-label">① 数据采集层</div>
                <div class="arch-layer">
                    <div class="arch-box accent">
                        <div class="arch-box-icon">🐙</div>
                        <div class="arch-box-name">GitHub Trending</div>
                        <div class="arch-box-tag">趋势项目抓取</div>
                    </div>
                    <div class="arch-box accent">
                        <div class="arch-box-icon">🔗</div>
                        <div class="arch-box-name">单仓库 URL</div>
                        <div class="arch-box-tag">指定仓库分析</div>
                    </div>
                </div>
                <div class="arch-connector"></div>
                <!-- 第二层：智能分析 -->
                <div class="arch-layer-label">② 智能分析层</div>
                <div class="arch-layer">
                    <div class="arch-box green">
                        <div class="arch-box-icon">📂</div>
                        <div class="arch-box-name">代码架构分析</div>
                        <div class="arch-box-tag">目录结构 + 技术栈</div>
                    </div>
                    <div class="arch-box green">
                        <div class="arch-box-icon">📄</div>
                        <div class="arch-box-name">README 解析</div>
                        <div class="arch-box-tag">功能特性提取</div>
                    </div>
                    <div class="arch-box green">
                        <div class="arch-box-icon">🤖</div>
                        <div class="arch-box-name">LLM 增强</div>
                        <div class="arch-box-tag">深度理解项目</div>
                    </div>
                </div>
                <div class="arch-connector"></div>
                <!-- 第三层：内容生成 -->
                <div class="arch-layer-label">③ 内容生成层</div>
                <div class="arch-layer">
                    <div class="arch-box">
                        <div class="arch-box-icon">📝</div>
                        <div class="arch-box-name">Markdown 文档</div>
                        <div class="arch-box-tag">项目深度解读</div>
                    </div>
                    <div class="arch-box">
                        <div class="arch-box-icon">💬</div>
                        <div class="arch-box-name">对话脚本</div>
                        <div class="arch-box-tag">双人 / 辩论 / 采访</div>
                    </div>
                    <div class="arch-box">
                        <div class="arch-box-icon">🎙️</div>
                        <div class="arch-box-name">TTS 音频</div>
                        <div class="arch-box-tag">双主播配音</div>
                    </div>
                </div>
                <div class="arch-connector"></div>
                <!-- 第四层：展示交互 -->
                <div class="arch-layer-label">④ 展示交互层</div>
                <div class="arch-layer">
                    <div class="arch-box purple">
                        <div class="arch-box-icon">📊</div>
                        <div class="arch-box-name">仪表盘</div>
                        <div class="arch-box-tag">项目管理 + 生成</div>
                    </div>
                    <div class="arch-box purple">
                        <div class="arch-box-icon">🎧</div>
                        <div class="arch-box-name">播放器</div>
                        <div class="arch-box-tag">波形可视化 + 倍速</div>
                    </div>
                    <div class="arch-box purple">
                        <div class="arch-box-icon">📖</div>
                        <div class="arch-box-name">详情页</div>
                        <div class="arch-box-tag">文档 + 脚本 + 问答</div>
                    </div>
                </div>
            </div>
        </div>

        <div class="toolbar">
            <input type="text" class="search-box" id="searchInput" placeholder="🔍 搜索项目名称或描述..." oninput="renderProjects()">
            <input type="text" class="quick-input" id="quickAnalyzeInput"
                placeholder="🔗 粘贴 GitHub URL 快速分析（如 github.com/owner/repo）"
                onkeydown="if(event.key==='Enter')quickAnalyze()">
            <button class="btn quick-btn" onclick="quickAnalyze()">⚡ 分析</button>
            <select id="filterLang" onchange="renderProjects()">
                <option value="">全部语言</option>
            </select>
            <select id="filterAudio" onchange="renderProjects()">
                <option value="">全部</option>
                <option value="has_audio">仅音频</option>
                <option value="no_audio">仅文档</option>
            </select>
            <select id="sortBy" onchange="renderProjects()">
                <option value="created_at">最新创建</option>
                <option value="stars">星标最多</option>
                <option value="name">名称</option>
                <option value="audio_duration">时长最长</option>
            </select>
        </div>
        <div class="projects-grid" id="projectsGrid"></div>
    </div>

    <!-- 批量操作浮窗 -->
    <div class="batch-bar" id="batchBar">
        <span class="batch-count" id="batchCount">已选 0 项</span>
        <button class="btn" id="compareBtn" onclick="generateComparison()" style="font-size:13px; padding:6px 14px; background: var(--accent);">🔍 生成对比</button>
        <button class="btn btn-danger" onclick="batchDelete()" style="font-size:13px; padding:6px 14px;">🗑 批量删除</button>
        <button class="btn btn-secondary" onclick="clearSelection()" style="font-size:13px; padding:6px 14px;">取消</button>
    </div>

    <!-- 对比任务状态条（项目列表页内）-->
    <div class="status-bar" id="compareStatusBar" style="margin: 0 32px 16px; max-width: 1336px;"></div>

    <!-- Tab 2: 生成任务 -->
    <div class="tab-content" id="content-generate">
        <!-- 工作流程图 -->
        <div class="flow-section">
            <div class="flow-title">🔄 工作流程</div>
            <div class="flow-desc">6 个步骤自动完成：从 GitHub 项目到可收听的双人对话播客</div>
            <div class="flow-chart">
                <div class="flow-step">
                    <div class="flow-step-icon">🐙</div>
                    <div class="flow-step-name">获取项目</div>
                    <div class="flow-step-detail">GitHub Trending 或指定仓库</div>
                </div>
                <div class="flow-arrow">→</div>
                <div class="flow-step">
                    <div class="flow-step-icon">📂</div>
                    <div class="flow-step-name">代码分析</div>
                    <div class="flow-step-detail">目录结构、技术栈、核心文件</div>
                </div>
                <div class="flow-arrow">→</div>
                <div class="flow-step">
                    <div class="flow-step-icon">📝</div>
                    <div class="flow-step-name">生成文档</div>
                    <div class="flow-step-detail">Markdown 深度解读</div>
                </div>
                <div class="flow-arrow">→</div>
                <div class="flow-step">
                    <div class="flow-step-icon">💬</div>
                    <div class="flow-step-name">编写脚本</div>
                    <div class="flow-step-detail">双主播对话 / 辩论 / 采访</div>
                </div>
                <div class="flow-arrow">→</div>
                <div class="flow-step">
                    <div class="flow-step-icon">🎙️</div>
                    <div class="flow-step-name">合成音频</div>
                    <div class="flow-step-detail">TTS 双人配音</div>
                </div>
                <div class="flow-arrow">→</div>
                <div class="flow-step">
                    <div class="flow-step-icon">🎧</div>
                    <div class="flow-step-name">在线收听</div>
                    <div class="flow-step-detail">播放器波形 + 倍速</div>
                </div>
            </div>
        </div>

        <p style="color: var(--text-dim); font-size: 14px; margin-bottom: 16px;">
            配置参数后点击运行，系统将自动获取 GitHub 趋势项目、分析代码架构并生成双人对话播客
        </p>

        <!-- 单仓库模式 -->
        <div style="background: var(--card-bg); border: 1px solid var(--border); border-radius: 12px; padding: 18px 20px; margin-bottom: 20px;">
            <div style="font-size: 15px; color: var(--accent); margin-bottom: 8px;">🔗 单仓库模式</div>
            <p style="color: var(--text-dim); font-size: 13px; margin-bottom: 12px;">
                粘贴任意 GitHub 仓库 URL，直接生成该项目的播客（填写后将忽略下方趋势参数 days/limit/language/min_stars）
            </p>
            <div class="form-row">
                <div class="form-group" style="flex: 1; min-width: 320px;">
                    <input type="text" id="repoUrl" class="search-box" style="width: 100%;"
                        placeholder="🔗 粘贴 GitHub 仓库 URL（如 https://github.com/owner/repo）">
                </div>
                <button class="btn" id="runRepoBtn" onclick="runSingleRepo()">▶ 生成</button>
            </div>
        </div>

        <div style="font-size: 14px; color: var(--text-dim); margin-bottom: 12px;">📦 趋势模式（按条件批量获取）</div>
        <div class="form-row">
            <div class="form-group"><label>最近天数</label><input type="number" id="days" value="7" min="1" max="365"></div>
            <div class="form-group"><label>项目数量</label><input type="number" id="limit" value="3" min="1" max="100"></div>
            <div class="form-group"><label>编程语言</label><input type="text" id="language" placeholder="python" value="python"></div>
            <div class="form-group"><label>最低 Star</label><input type="number" id="min_stars" value="100" min="0"></div>
            <div class="form-group"><label>输出语言</label><select id="lang"><option value="zh">中文</option><option value="en">English</option></select></div>
            <div class="form-group"><label>LLM 增强</label><select id="use_llm"><option value="true" selected>启用</option><option value="false">禁用</option></select></div>
            <div class="form-group"><label>播客风格</label><select id="style"><option value="dialogue" selected>双人对话</option><option value="debate">辩论式</option><option value="interview">采访式</option><option value="news">新闻播报</option><option value="story">故事式</option></select></div>
            <button class="btn" id="runBtn" onclick="runPipeline()">▶ 运行</button>
        </div>
        <div class="status-bar" id="statusBar"></div>
    </div>

    <!-- 底部导航栏 -->
    <nav class="bottom-nav" id="bottomNav">
        <a class="bottom-nav-item active" href="/" id="navHome">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/></svg>
            <span>首页</span>
        </a>
        <button class="bottom-nav-item" onclick="switchTab('projects')" id="navProjects">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/></svg>
            <span>项目</span>
        </button>
        <button class="bottom-nav-item" onclick="switchTab('generate')" id="navGenerate">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
            <span>生成</span>
        </button>
        <button class="bottom-nav-item" onclick="openPlayer()" id="navPlayer">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 18V5l12-2v13"/><circle cx="6" cy="18" r="3"/><circle cx="18" cy="16" r="3"/></svg>
            <span>播放器</span>
        </button>
        <button class="bottom-nav-item" onclick="toggleThemePanel()" id="navTheme">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/></svg>
            <span>主题</span>
        </button>
    </nav>

    <!-- 浮动播放器 -->
    <div class="player-bar hidden" id="playerBar">
        <div class="track-info">
            <span class="track-name" id="playerTrackName">—</span>
            <span class="track-status" id="playerStatus">播放中</span>
        </div>
        <span style="color:var(--text-dim); font-size:13px; flex:1; text-align:center;">🎵 正在独立播放器窗口中播放</span>
        <button class="btn btn-secondary" style="font-size:13px; padding:6px 14px;" onclick="focusPlayer()">🎵 显示播放器</button>
        <button class="player-close" onclick="closePlayer()">✕</button>
    </div>

    <!-- 书签说明弹窗（借鉴 Zread.ai 地址栏替换域名快捷方式） -->
    <div class="modal-overlay" id="bookmarkModal" onclick="if(event.target===this)closeBookmarkModal()">
        <div class="modal-box">
            <button class="modal-close" onclick="closeBookmarkModal()">✕</button>
            <h3>🔖 一键分析书签</h3>
            <p class="modal-desc">
                借鉴 Zread.ai「在地址栏替换域名即可访问」的快捷方式：将下方按钮拖到浏览器书签栏，
                之后在任意 GitHub 仓库页面点击书签，即可跳转到本工具分析该仓库。
            </p>
            <div class="bookmarklet-row">
                <a class="bookmarklet-link" id="bookmarkletLink" href="#">⚡ 用本工具分析</a>
                <span class="bookmarklet-hint">↑ 拖拽此按钮到浏览器书签栏</span>
            </div>
            <div class="modal-section">
                <div class="modal-label">书签代码（也可手动添加到书签）：</div>
                <pre class="code-block" id="bookmarkletCode"></pre>
                <button class="copy-btn" style="margin-top:8px;" onclick="copyBookmarklet()">📋 复制代码</button>
            </div>
            <div class="modal-section">
                <div class="modal-label">或直接在地址栏输入（替换域名即可）：</div>
                <span class="code-inline">http://&lt;host&gt;/r/owner/repo</span>
                <p class="modal-tip">例如：<code>/r/deepseek-ai/DeepSpec</code> 或 <code>/r/souzatharsis/podcastfy</code>。已存在的项目直接跳转详情页，未生成的项目会自动触发分析。</p>
            </div>
        </div>
    </div>

    <script>
        // ── 全局数据 ──
        const ALL_PROJECTS = {projects_json};
        let playlist = [];
        let currentTrack = 0;
        let isPlaying = false;
        let selectedProjects = new Set();
        const playerBar = document.getElementById('playerBar');

        // ── 多主题管理 ──
        function initTheme() {{
            var current = localStorage.getItem('gh-audio-theme') || 'dark';
            document.body.setAttribute('data-theme', current);
            document.querySelectorAll('.theme-dot').forEach(function(dot) {{
                dot.classList.toggle('active', dot.dataset.theme === current);
            }});
        }}
        function setTheme(theme) {{
            localStorage.setItem('gh-audio-theme', theme);
            document.body.setAttribute('data-theme', theme);
            document.querySelectorAll('.theme-dot').forEach(function(dot) {{
                dot.classList.toggle('active', dot.dataset.theme === theme);
            }});
            // 同步到其他窗口
            try {{ new BroadcastChannel('gh-audio-theme').postMessage(theme); }} catch(e) {{}}
        }}
        document.querySelectorAll('.theme-dot').forEach(function(dot) {{
            dot.addEventListener('click', function() {{ setTheme(dot.dataset.theme); }});
        }});
        // 跨窗口主题同步
        try {{
            new BroadcastChannel('gh-audio-theme').onmessage = function(e) {{
                if (e.data) {{
                    document.body.setAttribute('data-theme', e.data);
                    document.querySelectorAll('.theme-dot').forEach(function(dot) {{
                        dot.classList.toggle('active', dot.dataset.theme === e.data);
                    }});
                }}
            }};
        }} catch(e) {{}}
        initTheme();

        // ── 标签页 ──
        function switchTab(tabId) {{
            document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));
            document.querySelectorAll('.tab-btn').forEach(el => el.classList.remove('active'));
            document.getElementById('content-' + tabId).classList.add('active');
            document.getElementById('tab-' + tabId).classList.add('active');
            // 同步底部导航栏
            updateBottomNav(tabId);
        }}
        function updateBottomNav(tabId) {{
            document.querySelectorAll('.bottom-nav-item').forEach(el => el.classList.remove('active'));
            if (tabId === 'projects') document.getElementById('navProjects').classList.add('active');
            else if (tabId === 'generate') document.getElementById('navGenerate').classList.add('active');
            else document.getElementById('navHome').classList.add('active');
        }}
        // 底部"主题"按钮：弹出主题选择面板
        function toggleThemePanel() {{
            var switcher = document.getElementById('themeSwitcher');
            if (switcher) {{
                switcher.scrollIntoView({{ behavior: 'smooth', block: 'center' }});
                switcher.style.transition = 'transform 0.3s';
                switcher.style.transform = 'scale(1.3)';
                setTimeout(function() {{ switcher.style.transform = ''; }}, 600);
            }}
        }}

        // ── 格式化辅助 ──
        function formatSize(bytes) {{
            if (bytes > 1024*1024) return (bytes/1024/1024).toFixed(1) + ' MB';
            return (bytes/1024).toFixed(1) + ' KB';
        }}
        function formatDuration(seconds) {{
            if (!seconds) return '';
            const m = Math.floor(seconds / 60);
            const s = Math.floor(seconds % 60);
            return m + ':' + (s < 10 ? '0' : '') + s;
        }}
        function formatStars(n) {{
            if (n >= 1000) return (n/1000).toFixed(1) + 'k';
            return n;
        }}
        function escapeHtml(s) {{
            if (!s) return '';
            return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
        }}

        // ── 项目列表渲染（搜索 + 筛选 + 排序）──
        function renderProjects() {{
            const search = document.getElementById('searchInput').value.toLowerCase();
            const langFilter = document.getElementById('filterLang').value;
            const audioFilter = document.getElementById('filterAudio').value;
            const sortBy = document.getElementById('sortBy').value;

            let list = ALL_PROJECTS.filter(p => {{
                if (search && !p.name.toLowerCase().includes(search) && !(p.description||'').toLowerCase().includes(search)) return false;
                if (langFilter && p.language !== langFilter) return false;
                if (audioFilter === 'has_audio' && !p.has_audio) return false;
                if (audioFilter === 'no_audio' && p.has_audio) return false;
                return true;
            }});

            list.sort((a, b) => {{
                if (sortBy === 'stars') return (b.stars||0) - (a.stars||0);
                if (sortBy === 'name') return a.name.localeCompare(b.name);
                if (sortBy === 'audio_duration') return (b.audio_duration||0) - (a.audio_duration||0);
                return (b.created_at||0) - (a.created_at||0);
            }});

            const grid = document.getElementById('projectsGrid');
            if (list.length === 0) {{
                grid.innerHTML = '<div class="empty">没有匹配的项目</div>';
                return;
            }}

            grid.innerHTML = list.map(p => {{
                const audioBtn = p.has_audio
                    ? `<button class="card-btn play-btn" onclick="event.stopPropagation(); playInPlayer('${{p.audio_path}}', '${{escapeHtml(p.name)}}')">▶ 播放</button>
                       <button class="card-btn" onclick="event.stopPropagation(); openPlayer('${{p.name}}')" title="在播放器中打开">🎧</button>
                       <a class="card-btn" href="/file/${{p.audio_path}}" download>⬇</a>`
                    : '';
                const tags = [];
                if (p.language) tags.push(`<span class="tag lang">${{escapeHtml(p.language)}}</span>`);
                if (p.stars) tags.push(`<span class="tag stars">★ ${{formatStars(p.stars)}}</span>`);
                if (p.audio_duration) tags.push(`<span class="tag duration">⏱ ${{formatDuration(p.audio_duration)}}</span>`);
                if (p.license && p.license !== 'None') tags.push(`<span class="tag">${{escapeHtml(p.license)}}</span>`);
                const isSelected = selectedProjects.has(p.dir + '/' + p.name);
                const dir = p.dir;
                const name = encodeURIComponent(p.name);
                return `
                <div class="project-card ${{isSelected ? 'selected' : ''}}" onclick="window.location.href='/project/${{dir}}/${{name}}'">
                    <input type="checkbox" class="card-checkbox" ${{isSelected ? 'checked' : ''}}
                        onclick="event.stopPropagation(); toggleSelect('${{dir}}', '${{escapeHtml(p.name)}}')">
                    <div class="card-title">${{escapeHtml(p.name)}}</div>
                    <div class="card-desc">${{escapeHtml(p.description || '暂无描述')}}</div>
                    <div class="card-tags">${{tags.join('')}}</div>
                    <div class="card-footer">
                        <span class="card-size">${{formatSize(p.total_size)}}</span>
                        <div class="card-actions">
                            ${{audioBtn}}
                            <a class="card-btn" href="/file/${{p.md_path}}" download title="下载文档">📄</a>
                            <button class="card-btn delete-btn" onclick="event.stopPropagation(); deleteProject('${{dir}}', '${{escapeHtml(p.name)}}')" title="删除">🗑</button>
                        </div>
                    </div>
                </div>`;
            }}).join('');

            updateBatchBar();
        }}

        // ── 语言筛选下拉 ──
        function initLangFilter() {{
            const langs = [...new Set(ALL_PROJECTS.map(p => p.language).filter(Boolean))];
            const sel = document.getElementById('filterLang');
            langs.forEach(l => {{
                const opt = document.createElement('option');
                opt.value = l; opt.textContent = l;
                sel.appendChild(opt);
            }});
        }}

        // ── 总时长统计 ──
        function updateTotalDuration() {{
            const total = ALL_PROJECTS.reduce((sum, p) => sum + (p.audio_duration || 0), 0);
            const h = Math.floor(total / 3600);
            const m = Math.floor((total % 3600) / 60);
            document.getElementById('stat-duration').textContent = h > 0 ? `${{h}}h${{m}}m` : `${{m}}m`;
        }}

        // ── 批量选择 ──
        function toggleSelect(dir, name) {{
            const key = dir + '/' + name;
            if (selectedProjects.has(key)) selectedProjects.delete(key);
            else selectedProjects.add(key);
            renderProjects();
        }}
        function updateBatchBar() {{
            const bar = document.getElementById('batchBar');
            const count = selectedProjects.size;
            const countLabel = document.getElementById('batchCount');
            const compareBtn = document.getElementById('compareBtn');
            countLabel.textContent = `已选 ${{count}} 项`;
            bar.classList.toggle('visible', count > 0);
            // 对比按钮仅在选中 2-3 个项目时可用
            const canCompare = count >= 2 && count <= 3;
            compareBtn.disabled = !canCompare;
            compareBtn.style.opacity = canCompare ? '1' : '0.4';
            compareBtn.style.cursor = canCompare ? 'pointer' : 'not-allowed';
            if (count === 1) countLabel.textContent = `已选 1 项（对比需选 2-3 个）`;
            else if (count > 3) countLabel.textContent = `已选 ${{count}} 项（对比最多 3 个）`;
        }}
        function clearSelection() {{
            selectedProjects.clear();
            renderProjects();
        }}
        async function batchDelete() {{
            if (!confirm(`确定删除选中的 ${{selectedProjects.size}} 个项目？`)) return;
            for (const key of selectedProjects) {{
                const [dir, ...nameParts] = key.split('/');
                const name = nameParts.join('/');
                await fetch(`/api/delete/${{dir}}/${{encodeURIComponent(name)}}`, {{ method: 'POST' }});
            }}
            selectedProjects.clear();
            location.reload();
        }}

        // ── 多仓库对比（借鉴 Zread.ai）──
        async function generateComparison() {{
            const count = selectedProjects.size;
            if (count < 2 || count > 3) {{
                alert('请选择 2-3 个项目进行对比');
                return;
            }}
            const compareBtn = document.getElementById('compareBtn');
            const bar = document.getElementById('compareStatusBar');
            compareBtn.disabled = true;

            const projects = [];
            for (const key of selectedProjects) {{
                const [dir, ...nameParts] = key.split('/');
                projects.push({{ dir: dir, name: nameParts.join('/') }});
            }}

            bar.className = 'status-bar running';
            bar.innerHTML = `<span class="spinner"></span>正在生成 ${{projects.length}} 个项目的对比分析（LLM + TTS，约需 1 分钟）...`;
            // 滚动到状态条让用户看到进度
            bar.scrollIntoView({{ behavior: 'smooth', block: 'center' }});

            try {{
                const resp = await fetch('/api/compare', {{
                    method: 'POST', headers: {{'Content-Type': 'application/json'}},
                    body: JSON.stringify({{ projects: projects }}),
                }});
                const data = await resp.json();
                if (resp.status === 202) {{
                    pollComparisonStatus();
                }} else {{
                    bar.className = 'status-bar error';
                    bar.textContent = '❌ ' + (data.error || '启动失败');
                    compareBtn.disabled = false;
                }}
            }} catch(e) {{
                bar.className = 'status-bar error';
                bar.textContent = '❌ 请求失败: ' + e.message;
                compareBtn.disabled = false;
            }}
        }}

        async function pollComparisonStatus() {{
            const bar = document.getElementById('compareStatusBar');
            const compareBtn = document.getElementById('compareBtn');
            const check = async () => {{
                try {{
                    const resp = await fetch('/api/status');
                    const data = await resp.json();
                    if (data.running) {{
                        bar.className = 'status-bar running';
                        bar.innerHTML = '<span class="spinner"></span>正在生成对比文档和对比播客...';
                        setTimeout(check, 3000);
                    }} else if (data.last_result && data.last_result.type === 'comparison') {{
                        const r = data.last_result;
                        bar.className = 'status-bar success';
                        bar.innerHTML = `✅ 对比完成！已生成对比文档${{r.audio_count ? '和对比播客' : ''}}，3 秒后跳转到对比详情页...`;
                        setTimeout(() => {{ window.location.href = r.project_url; }}, 3000);
                    }} else if (data.last_error) {{
                        bar.className = 'status-bar error';
                        bar.textContent = '❌ 对比失败: ' + data.last_error;
                        compareBtn.disabled = false;
                    }} else {{
                        bar.className = 'status-bar running';
                        bar.innerHTML = '<span class="spinner"></span>等待中...';
                        setTimeout(check, 2000);
                    }}
                }} catch(e) {{
                    setTimeout(check, 3000);
                }}
            }};
            check();
        }}

        // ── 弹出播放器窗口（持久化，页面切换不中断） ──
        var playerWin = null;
        function openPlayer(trackName) {{
            var url = '/player' + (trackName ? '?play=' + encodeURIComponent(trackName) : '');
            playerWin = window.open(url, 'ghAudioPlayer',
                'width=900,height=640,menubar=no,toolbar=no,location=no,status=no');
            if (playerWin) {{
                playerWin.focus();
            }}
        }}

        // ── 播放器 ──
        function playInPlayer(audioPath, trackName) {{
            // 优先在弹出播放器窗口中播放
            if (playerWin && !playerWin.closed) {{
                playerWin.postMessage({{ type: 'playTrack', name: trackName }}, '*');
                playerWin.focus();
                return;
            }}
            // 否则打开弹出窗口
            openPlayer(trackName);
        }}
        function playTrack(index) {{
            if (index < 0 || index >= playlist.length) return;
            currentTrack = index;
            playInPlayer(playlist[index].audio_path, playlist[index].name);
        }}
        function togglePlayAll() {{
            if (playerWin && !playerWin.closed) {{
                playerWin.postMessage({{ type: 'togglePlay' }}, '*');
            }} else {{
                openPlayer();
            }}
        }}
        function playNext() {{
            if (playerWin && !playerWin.closed) playerWin.postMessage({{ type: 'next' }}, '*');
        }}
        function playPrev() {{
            if (playerWin && !playerWin.closed) playerWin.postMessage({{ type: 'prev' }}, '*');
        }}
        function closePlayer() {{
            if (playerWin && !playerWin.closed) {{
                playerWin.postMessage({{ type: 'pause' }}, '*');
            }}
            isPlaying = false; playerBar.classList.add('hidden');
            document.getElementById('bottomNav').classList.remove('with-player');
        }}
        function focusPlayer() {{
            if (playerWin && !playerWin.closed) {{
                playerWin.focus();
            }} else {{
                openPlayer();
            }}
        }}

        // ── 接收弹出播放器的状态同步 ──
        var dashboardBC = null;
        try {{ dashboardBC = new BroadcastChannel('gh-audio-player'); }} catch(e) {{}}
        if (dashboardBC) {{
            dashboardBC.onmessage = function(event) {{
                var msg = event.data;
                if (!msg) return;
                if (msg.type === 'playing') {{
                    isPlaying = true;
                    playerBar.classList.remove('hidden');
                    document.getElementById('bottomNav').classList.add('with-player');
                    document.getElementById('playerTrackName').textContent = msg.track.replace('_', '/');
                    document.getElementById('playerStatus').textContent = '播放中';
                }} else if (msg.type === 'paused') {{
                    isPlaying = false;
                    document.getElementById('playerStatus').textContent = '已暂停';
                }} else if (msg.type === 'ended') {{
                    isPlaying = false;
                    document.getElementById('playerStatus').textContent = '播放完毕';
                }}
            }};
        }}

        // ── 播放列表（仅用于浮动播放器的曲目数据） ──
        function loadPlaylist() {{
            playlist = ALL_PROJECTS.filter(p => p.has_audio);
            document.getElementById('badge-projects').textContent = ALL_PROJECTS.length;
        }}

        // ── 删除 ──
        async function deleteProject(dir, name) {{
            if (!confirm(`确定删除「${{name}}」的所有文件？`)) return;
            try {{
                const resp = await fetch(`/api/delete/${{dir}}/${{encodeURIComponent(name)}}`, {{ method: 'POST' }});
                if (resp.ok) {{ alert('已删除'); location.reload(); }}
                else {{ const d = await resp.json(); alert('删除失败: ' + (d.error || '')); }}
            }} catch(e) {{ alert('请求失败: ' + e.message); }}
        }}

        // ── 单仓库模式 ──
        async function runSingleRepo() {{
            const repoUrl = document.getElementById('repoUrl').value.trim();
            const bar = document.getElementById('statusBar');
            const repoBtn = document.getElementById('runRepoBtn');
            const trendBtn = document.getElementById('runBtn');
            if (!repoUrl) {{
                bar.className = 'status-bar error';
                bar.textContent = '请输入 GitHub 仓库 URL';
                return;
            }}
            repoBtn.disabled = true;
            trendBtn.disabled = true;
            const params = {{ repo_url: repoUrl }};
            bar.className = 'status-bar running';
            bar.innerHTML = '<span class="spinner"></span>单仓库任务已启动...';
            try {{
                const resp = await fetch('/api/run', {{
                    method: 'POST', headers: {{'Content-Type': 'application/json'}},
                    body: JSON.stringify(params),
                }});
                const data = await resp.json();
                if (resp.status === 202) pollStatus();
                else {{ bar.className = 'status-bar error'; bar.textContent = data.error || '启动失败'; repoBtn.disabled = false; trendBtn.disabled = false; }}
            }} catch(e) {{ bar.className = 'status-bar error'; bar.textContent = '请求失败: ' + e.message; repoBtn.disabled = false; trendBtn.disabled = false; }}
        }}

        // ── 运行管道 ──
        async function runPipeline() {{
            const btn = document.getElementById('runBtn');
            const bar = document.getElementById('statusBar');
            btn.disabled = true;
            const params = {{
                days: parseInt(document.getElementById('days').value),
                limit: parseInt(document.getElementById('limit').value),
                language: document.getElementById('language').value || null,
                min_stars: parseInt(document.getElementById('min_stars').value),
                lang: document.getElementById('lang').value,
                use_llm: document.getElementById('use_llm').value === 'true',
                style: document.getElementById('style').value,
            }};
            bar.className = 'status-bar running';
            bar.innerHTML = '<span class="spinner"></span>任务已启动...';
            try {{
                const resp = await fetch('/api/run', {{
                    method: 'POST', headers: {{'Content-Type': 'application/json'}},
                    body: JSON.stringify(params),
                }});
                const data = await resp.json();
                if (resp.status === 202) pollStatus();
                else {{ bar.className = 'status-bar error'; bar.textContent = data.error || '启动失败'; btn.disabled = false; }}
            }} catch(e) {{ bar.className = 'status-bar error'; bar.textContent = '请求失败: ' + e.message; btn.disabled = false; }}
        }}
        async function pollStatus() {{
            const bar = document.getElementById('statusBar');
            const trendBtn = document.getElementById('runBtn');
            const repoBtn = document.getElementById('runRepoBtn');
            const resetBtns = () => {{ trendBtn.disabled = false; repoBtn.disabled = false; }};
            const check = async () => {{
                try {{
                    const resp = await fetch('/api/status');
                    const data = await resp.json();
                    if (data.running) {{ bar.className = 'status-bar running'; bar.innerHTML = '<span class="spinner"></span>正在处理中...'; setTimeout(check, 3000); }}
                    else if (data.last_result) {{ bar.className = 'status-bar success'; bar.innerHTML = `✅ 完成！生成 ${{data.last_result.doc_count}} 篇文档 + ${{data.last_result.audio_count}} 个音频${{data.last_result.skipped ? '，跳过 ' + data.last_result.skipped + ' 个已存在' : ''}}。3 秒后刷新...`; setTimeout(() => location.reload(), 3000); }}
                    else if (data.last_error) {{ bar.className = 'status-bar error'; bar.textContent = '❌ ' + data.last_error; resetBtns(); }}
                    else {{ bar.className = 'status-bar running'; bar.innerHTML = '<span class="spinner"></span>等待中...'; setTimeout(check, 2000); }}
                }} catch(e) {{ setTimeout(check, 3000); }}
            }};
            check();
        }}

        // ── 快捷 URL / 快速分析 / 书签 ──
        // 从 GitHub URL 或 owner/repo 文本中解析出 owner/repo（避免使用含反斜杠的正则）
        function parseGithubSlug(raw) {{
            if (!raw) return null;
            var idx = raw.indexOf('github.com/');
            if (idx >= 0) {{
                var rest = raw.substring(idx + 11).split('?')[0].split('#')[0];
                var parts = rest.split('/');
                if (parts.length >= 2 && parts[0] && parts[1]) {{
                    var repo = parts[1];
                    if (repo.endsWith('.git')) repo = repo.substring(0, repo.length - 4);
                    return parts[0] + '/' + repo;
                }}
            }}
            // 兼容直接输入 owner/repo
            if (raw.indexOf(' ') < 0 && raw.indexOf('/') >= 0) {{
                var ps = raw.split('/');
                if (ps.length >= 2 && ps[0] && ps[1]) {{
                    var repo2 = ps[1];
                    if (repo2.endsWith('.git')) repo2 = repo2.substring(0, repo2.length - 4);
                    return ps[0] + '/' + repo2;
                }}
            }}
            return null;
        }}

        // 快速分析：粘贴 GitHub URL → 跳转 /r/owner/repo
        function quickAnalyze() {{
            var raw = (document.getElementById('quickAnalyzeInput').value || '').trim();
            var slug = parseGithubSlug(raw);
            if (slug) {{
                window.location.href = '/r/' + slug;
            }} else {{
                alert('请粘贴有效的 GitHub 仓库 URL，例如：https://github.com/owner/repo');
            }}
        }}

        // 生成书签小工具代码（动态注入当前 host，拖到书签栏后可在任意 GitHub 页面使用）
        function buildBookmarklet() {{
            var origin = window.location.origin || (window.location.protocol + '//' + window.location.host);
            var code = "javascript:(function(){{"
                + "var h=window.location.href;"
                + "var i=h.indexOf('github.com/');"
                + "if(i<0){{alert('请在 GitHub 仓库页面使用此书签');return;}}"
                + "var rest=h.substring(i+11).split('?')[0].split('#')[0];"
                + "var parts=rest.split('/');"
                + "if(parts.length<2||!parts[0]||!parts[1]){{alert('请在 GitHub 仓库页面使用此书签');return;}}"
                + "window.open('" + origin + "/r/'+parts[0]+'/'+parts[1],'_blank');"
                + "}})();";
            return code;
        }}

        function showBookmarkModal() {{
            var code = buildBookmarklet();
            var link = document.getElementById('bookmarkletLink');
            if (link) link.href = code;
            var codeEl = document.getElementById('bookmarkletCode');
            if (codeEl) codeEl.textContent = code;
            var modal = document.getElementById('bookmarkModal');
            if (modal) modal.classList.add('visible');
        }}

        function closeBookmarkModal() {{
            var modal = document.getElementById('bookmarkModal');
            if (modal) modal.classList.remove('visible');
        }}

        function copyBookmarklet() {{
            var code = buildBookmarklet();
            try {{
                if (navigator.clipboard && navigator.clipboard.writeText) {{
                    navigator.clipboard.writeText(code).then(function() {{ alert('已复制书签代码到剪贴板'); }});
                }} else {{
                    var ta = document.createElement('textarea');
                    ta.value = code; document.body.appendChild(ta); ta.select();
                    document.execCommand('copy'); document.body.removeChild(ta);
                    alert('已复制书签代码到剪贴板');
                }}
            }} catch(e) {{
                alert('复制失败，请手动复制上方代码');
            }}
        }}

        // auto_generate 参数检测：从 /r/ 跳转过来且项目不存在时，自动调用 /api/run 生成
        function checkAutoGenerate() {{
            var params = new URLSearchParams(window.location.search);
            var ag = params.get('auto_generate');
            if (!ag) return;
            // 清理 URL，避免刷新时重复触发
            try {{ window.history.replaceState({{}}, '', window.location.pathname); }} catch(e) {{}}
            switchTab('generate');
            var repoUrl;
            if (ag.indexOf('/') >= 0) {{
                repoUrl = 'https://github.com/' + ag;
            }} else if (ag.indexOf('_') >= 0) {{
                repoUrl = 'https://github.com/' + ag.replace('_', '/');
            }} else {{
                repoUrl = 'https://github.com/' + ag;
            }}
            var input = document.getElementById('repoUrl');
            if (input) input.value = repoUrl;
            var bar = document.getElementById('statusBar');
            if (bar) {{
                bar.className = 'status-bar running';
                bar.innerHTML = '<span class="spinner"></span>检测到快捷链接，正在分析 ' + ag + ' ...';
            }}
            // 复用已有的单仓库生成流程
            if (typeof runSingleRepo === 'function') runSingleRepo();
        }}

        // ── 初始化 ──
        initLangFilter();
        renderProjects();
        updateTotalDuration();
        loadPlaylist();
        checkAutoGenerate();
    </script>
</body>
</html>
"""


# ── 播放器页面模板 ──
PLAYER_HTML = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>播放器 - GitHub Trending Audio</title>
    <script src="https://cdn.jsdelivr.net/npm/howler@2.2.4/dist/howler.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/wavesurfer.js@7/dist/wavesurfer.min.js"></script>
    <style>
        /* ═══ 多主题系统 ═══ */
        :root {{ --radius: 12px; --transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1); }}
        [data-theme="dark"] {{
            --bg: #0d1117; --bg-gradient: radial-gradient(ellipse at top, #161b22 0%, #0d1117 60%);
            --card-bg: #161b22; --card-hover: #1c2330;
            --border: #30363d; --border-light: #21262d;
            --text: #e6edf3; --text-dim: #8b949e;
            --accent: #58a6ff; --accent-glow: rgba(88,166,255,0.15);
            --green: #3fb950; --red: #f85149; --yellow: #d29922; --purple: #bc8cff;
            --hover-bg: #1c2128;
            --shadow-sm: 0 2px 8px rgba(0,0,0,0.2); --shadow-md: 0 4px 16px rgba(0,0,0,0.3); --shadow-lg: 0 8px 32px rgba(0,0,0,0.4);
            --header-bg: rgba(22,27,34,0.6); --glass-blur: blur(12px);
        }}
        [data-theme="light"] {{
            --bg: #f6f8fa; --bg-gradient: radial-gradient(ellipse at top, #ffffff 0%, #f6f8fa 60%);
            --card-bg: #ffffff; --card-hover: #f0f3f6;
            --border: #d0d7de; --border-light: #eaeef2;
            --text: #1f2328; --text-dim: #656d76;
            --accent: #0969da; --accent-glow: rgba(9,105,218,0.12);
            --green: #1a7f37; --red: #cf222e; --yellow: #9a6700; --purple: #8250df;
            --hover-bg: #eaeef2;
            --shadow-sm: 0 2px 8px rgba(0,0,0,0.06); --shadow-md: 0 4px 16px rgba(0,0,0,0.1); --shadow-lg: 0 8px 32px rgba(0,0,0,0.12);
            --header-bg: rgba(255,255,255,0.6); --glass-blur: blur(12px);
        }}
        [data-theme="midnight"] {{
            --bg: #0f0f23; --bg-gradient: radial-gradient(ellipse at top, #1a1a3e 0%, #0f0f23 60%);
            --card-bg: #1a1a3e; --card-hover: #252550;
            --border: #3a3a6e; --border-light: #2a2a52;
            --text: #e0e0ff; --text-dim: #8888bb;
            --accent: #7c7cff; --accent-glow: rgba(124,124,255,0.18);
            --green: #50e3a0; --red: #ff6b8a; --yellow: #ffd966; --purple: #c084fc;
            --hover-bg: #252550;
            --shadow-sm: 0 2px 8px rgba(0,0,0,0.3); --shadow-md: 0 4px 16px rgba(0,0,0,0.4); --shadow-lg: 0 8px 32px rgba(0,0,0,0.5);
            --header-bg: rgba(26,26,62,0.6); --glass-blur: blur(12px);
        }}
        [data-theme="nord"] {{
            --bg: #2e3440; --bg-gradient: radial-gradient(ellipse at top, #3b4252 0%, #2e3440 60%);
            --card-bg: #3b4252; --card-hover: #434c5e;
            --border: #4c566a; --border-light: #3f485a;
            --text: #eceff4; --text-dim: #81a1c1;
            --accent: #88c0d0; --accent-glow: rgba(136,192,208,0.15);
            --green: #a3be8c; --red: #bf616a; --yellow: #ebcb8b; --purple: #b48ead;
            --hover-bg: #434c5e;
            --shadow-sm: 0 2px 8px rgba(0,0,0,0.25); --shadow-md: 0 4px 16px rgba(0,0,0,0.35); --shadow-lg: 0 8px 32px rgba(0,0,0,0.45);
            --header-bg: rgba(59,66,82,0.6); --glass-blur: blur(12px);
        }}
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, 'Segoe UI', 'Noto Sans CJK SC', sans-serif;
            background: var(--bg-gradient); color: var(--text);
            display: flex; height: 100vh; overflow: hidden;
        }}
        /* ── 主题切换器 ── */
        .theme-switcher {{
            display: flex; gap: 6px; align-items: center;
            padding: 4px 8px; border-radius: 20px;
            background: var(--card-bg); border: 1px solid var(--border-light);
        }}
        .theme-dot {{
            width: 16px; height: 16px; border-radius: 50%;
            border: 2px solid var(--border); cursor: pointer;
            transition: transform 0.2s, box-shadow 0.2s; padding: 0;
        }}
        .theme-dot:hover {{ transform: scale(1.2); }}
        .theme-dot.active {{
            transform: scale(1.25);
            box-shadow: 0 0 0 2px var(--accent), 0 0 8px var(--accent-glow);
        }}

        /* ── 左侧播放列表 ── */
        .playlist-panel {{
            width: 320px; min-width: 320px;
            background: var(--card-bg);
            border-right: 1px solid var(--border);
            display: flex; flex-direction: column;
            transition: width 0.25s ease, min-width 0.25s ease;
            overflow: hidden;
        }}
        .playlist-panel.collapsed {{
            width: 0; min-width: 0;
            border-right: none;
        }}
        .sidebar-toggle {{
            position: absolute; left: 320px; top: 50%;
            transform: translateY(-50%);
            width: 22px; height: 48px;
            background: var(--card-bg); border: 1px solid var(--border);
            border-left: none; border-radius: 0 8px 8px 0;
            color: var(--text-dim); cursor: pointer;
            display: flex; align-items: center; justify-content: center;
            font-size: 12px; z-index: 100; transition: left 0.25s ease, color 0.15s, background 0.15s;
        }}
        .sidebar-toggle:hover {{ color: var(--accent); background: var(--card-hover); }}
        .sidebar-toggle.collapsed {{ left: 0; }}
        .playlist-header {{
            padding: 20px; border-bottom: 1px solid var(--border);
        }}
        .playlist-header h1 {{
            font-size: 17px; display: flex; align-items: center; gap: 8px;
            background: linear-gradient(135deg, var(--accent), var(--purple));
            -webkit-background-clip: text; -webkit-text-fill-color: transparent;
            background-clip: text;
        }}
        .playlist-header .stats {{
            font-size: 12px; color: var(--text-dim); margin-top: 4px;
        }}
        .playlist-search {{
            padding: 12px 16px; border-bottom: 1px solid var(--border);
        }}
        .playlist-search input {{
            width: 100%; padding: 9px 14px;
            background: var(--bg); border: 1px solid var(--border-light);
            border-radius: 8px; color: var(--text); font-size: 13px;
            transition: var(--transition);
        }}
        .playlist-search input:focus {{
            outline: none; border-color: var(--accent); box-shadow: 0 0 0 3px var(--accent-glow);
        }}
        .playlist-items {{
            flex: 1; overflow-y: auto; padding: 8px;
        }}
        .playlist-items::-webkit-scrollbar {{ width: 6px; }}
        .playlist-items::-webkit-scrollbar-track {{ background: transparent; }}
        .playlist-items::-webkit-scrollbar-thumb {{ background: var(--border); border-radius: 3px; }}
        .playlist-items::-webkit-scrollbar-thumb:hover {{ background: var(--text-dim); }}
        .track-item {{
            display: flex; align-items: center; gap: 12px;
            padding: 10px 12px; border-radius: 8px;
            cursor: pointer; transition: var(--transition);
            margin-bottom: 4px;
        }}
        .track-item:hover {{ background: var(--hover-bg); }}
        .track-item.active {{
            background: var(--accent-glow);
            border-left: 3px solid var(--accent);
            padding-left: 9px;
        }}
        .track-cover {{
            width: 40px; height: 40px; border-radius: 8px;
            display: flex; align-items: center; justify-content: center;
            font-size: 18px; flex-shrink: 0;
            box-shadow: 0 2px 8px rgba(0,0,0,0.2);
        }}
        .track-number {{
            font-size: 14px; font-weight: 700; color: #fff;
            text-shadow: 0 1px 2px rgba(0,0,0,0.3);
        }}
        .empty-state {{
            text-align: center; padding: 60px 20px; color: var(--text-dim);
        }}
        .empty-state .icon {{ font-size: 48px; margin-bottom: 12px; opacity: 0.5; }}
        .empty-state .empty-hint {{ font-size: 12px; margin-top: 8px; opacity: 0.7; }}
        .track-info {{ flex: 1; min-width: 0; }}
        .track-name {{
            font-size: 13px; font-weight: 500; white-space: nowrap;
            overflow: hidden; text-overflow: ellipsis;
        }}
        .track-meta {{
            font-size: 11px; color: var(--text-dim); margin-top: 2px;
            display: flex; gap: 8px; align-items: center;
        }}
        .track-duration {{
            font-size: 11px; color: var(--text-dim); flex-shrink: 0;
            font-variant-numeric: tabular-nums;
        }}
        .now-playing-icon {{
            display: inline-block; width: 14px; height: 14px;
        }}
        .now-playing-icon .bar {{
            display: inline-block; width: 3px; background: var(--accent);
            border-radius: 2px; margin-right: 1px;
            animation: bounce 0.8s ease-in-out infinite;
        }}
        .now-playing-icon .bar:nth-child(2) {{ animation-delay: 0.2s; }}
        .now-playing-icon .bar:nth-child(3) {{ animation-delay: 0.4s; }}
        @keyframes bounce {{
            0%, 100% {{ height: 4px; }}
            50% {{ height: 12px; }}
        }}

        /* ── 右侧播放器主区域 ── */
        .player-panel {{
            flex: 1; display: flex; flex-direction: column;
            background: transparent;
        }}
        .player-top-bar {{
            display: flex; align-items: center; gap: 16px; flex-wrap: wrap;
            padding: 14px 24px; border-bottom: 1px solid var(--border);
            background: var(--header-bg); backdrop-filter: var(--glass-blur);
        }}
        .player-top-bar a {{
            color: var(--accent); text-decoration: none; font-size: 14px;
            transition: var(--transition);
        }}
        .player-top-bar a:hover {{ opacity: 0.8; }}
        .player-top-bar .player-title {{
            font-size: 15px; font-weight: 500; color: var(--text-dim);
        }}

        .player-content {{
            flex: 1; display: flex; flex-direction: column;
            align-items: center; justify-content: center;
            padding: 40px; overflow-y: auto;
        }}
        .player-content::-webkit-scrollbar {{ width: 6px; }}
        .player-content::-webkit-scrollbar-thumb {{ background: var(--border); border-radius: 3px; }}

        /* 封面区域 */
        .cover-section {{
            display: flex; flex-direction: column; align-items: center;
            margin-bottom: 32px;
        }}
        .cover-art {{
            width: 200px; height: 200px; border-radius: 50%;
            background: linear-gradient(135deg, var(--accent) 0%, var(--purple) 40%, var(--green) 100%);
            display: flex; align-items: center; justify-content: center;
            font-size: 64px; box-shadow: 0 20px 60px rgba(0,0,0,0.5), 0 0 80px rgba(88,166,255,0.15);
            transition: transform 0.5s cubic-bezier(0.4, 0, 0.2, 1);
            position: relative; overflow: hidden;
        }}
        .cover-art.playing {{
            transform: scale(1.05);
            animation: rotate 20s linear infinite;
        }}
        @keyframes rotate {{
            from {{ transform: scale(1.05) rotate(0deg); }}
            to {{ transform: scale(1.05) rotate(360deg); }}
        }}
        .cover-art::before {{
            content: ''; position: absolute;
            width: 50px; height: 50px; border-radius: 50%;
            background: var(--bg); top: 50%; left: 50%;
            transform: translate(-50%, -50%);
            box-shadow: inset 0 0 0 6px var(--card-bg), 0 0 0 1px var(--border);
            z-index: 2;
        }}
        .cover-art .cover-emoji {{
            position: absolute; z-index: 1;
            filter: drop-shadow(0 2px 8px rgba(0,0,0,0.3));
        }}
        .cover-info {{
            text-align: center; margin-top: 24px;
        }}
        .cover-info h2 {{
            font-size: 22px; font-weight: 600; margin-bottom: 6px;
            background: linear-gradient(135deg, var(--text), var(--text-dim));
            -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        }}
        .cover-info .subtitle {{
            font-size: 14px; color: var(--text-dim);
            max-width: 400px; line-height: 1.5;
        }}

        /* 波形 */
        .waveform-container {{
            width: 100%; max-width: 600px; margin-bottom: 24px;
            padding: 16px 0;
        }}
        #waveform {{ width: 100%; }}

        /* 控制栏 */
        .controls {{
            display: flex; align-items: center; gap: 24px;
            margin-bottom: 16px;
        }}
        .ctrl-btn {{
            background: none; border: none; color: var(--text-dim);
            font-size: 20px; cursor: pointer; padding: 10px;
            transition: var(--transition); display: flex; align-items: center;
            border-radius: 50%; width: 42px; height: 42px; justify-content: center;
        }}
        .ctrl-btn:hover {{ color: var(--accent); background: var(--accent-glow); }}
        .ctrl-btn.play-btn {{
            width: 56px; height: 56px; border-radius: 50%;
            background: linear-gradient(135deg, var(--accent), #4a90e2); color: #fff;
            font-size: 22px; justify-content: center;
            box-shadow: 0 4px 16px rgba(88,166,255,0.3);
        }}
        .ctrl-btn.play-btn:hover {{
            transform: scale(1.08); color: #fff;
            box-shadow: 0 6px 24px rgba(88,166,255,0.4);
        }}

        /* 进度条 */
        .progress-section {{
            width: 100%; max-width: 600px;
            display: flex; align-items: center; gap: 12px;
            margin-bottom: 24px;
        }}
        .progress-bar-wrap {{
            flex: 1; height: 6px; background: var(--border);
            border-radius: 3px; cursor: pointer; position: relative;
            transition: height 0.15s;
        }}
        .progress-bar-wrap:hover {{ height: 8px; }}
        .progress-bar-wrap:hover .progress-fill {{ opacity: 0.9; }}
        .progress-fill {{
            height: 100%; border-radius: 3px;
            background: linear-gradient(90deg, var(--accent), var(--purple));
            width: 0%; transition: width 0.1s;
        }}
        .progress-fill::after {{
            content: ''; position: absolute; right: -5px; top: 50%;
            transform: translateY(-50%); width: 12px; height: 12px;
            border-radius: 50%; background: #fff;
            box-shadow: 0 2px 6px rgba(0,0,0,0.3); opacity: 0;
            transition: opacity 0.15s;
        }}
        .progress-bar-wrap:hover .progress-fill::after {{ opacity: 1; }}
        .time-display {{
            font-size: 12px; color: var(--text-dim); min-width: 38px;
            text-align: center; font-variant-numeric: tabular-nums;
        }}

        /* 底部工具栏 */
        .bottom-bar {{
            display: flex; align-items: center; gap: 24px;
            padding: 14px 24px; border-top: 1px solid var(--border);
            background: var(--header-bg); backdrop-filter: var(--glass-blur);
        }}
        .speed-control {{
            display: flex; align-items: center; gap: 8px;
        }}
        .speed-control label {{
            font-size: 13px; color: var(--text-dim);
        }}
        .speed-control select {{
            background: var(--bg); border: 1px solid var(--border-light);
            color: var(--text); border-radius: 8px;
            padding: 6px 10px; font-size: 13px; cursor: pointer;
            transition: var(--transition);
        }}
        .speed-control select:hover {{ border-color: var(--accent); }}
        .speed-control select:focus {{ outline: none; border-color: var(--accent); box-shadow: 0 0 0 3px var(--accent-glow); }}
        .volume-control {{
            display: flex; align-items: center; gap: 8px;
            margin-left: auto;
        }}
        .volume-control input[type="range"] {{
            width: 80px; accent-color: var(--accent); cursor: pointer;
        }}
        .download-btn {{
            background: var(--card-bg); border: 1px solid var(--border-light);
            color: var(--text); border-radius: 8px;
            padding: 8px 16px; font-size: 13px; cursor: pointer;
            text-decoration: none; display: flex; align-items: center; gap: 6px;
            transition: var(--transition);
        }}
        .download-btn:hover {{ border-color: var(--accent); color: var(--accent); box-shadow: 0 0 0 3px var(--accent-glow); }}

        /* 脚本预览 */
        .script-section {{
            width: 100%; max-width: 600px; margin-top: 8px;
        }}
        .script-section summary {{
            cursor: pointer; font-size: 14px; color: var(--text-dim);
            padding: 8px 0; user-select: none;
        }}
        .script-section summary:hover {{ color: var(--accent); }}
        .script-content {{
            background: var(--card-bg); border: 1px solid var(--border);
            border-radius: 8px; padding: 16px; margin-top: 8px;
            max-height: 300px; overflow-y: auto;
            white-space: pre-wrap; font-size: 13px; line-height: 1.6;
        }}

        /* 空状态 */
        .empty-state {{
            text-align: center; color: var(--text-dim); padding: 60px;
        }}
        .empty-state .icon {{ font-size: 60px; margin-bottom: 16px; }}
    </style>
</head>
<body data-theme="dark">
    <script>
        (function() {{
            var t = localStorage.getItem('gh-audio-theme') || 'dark';
            document.body.setAttribute('data-theme', t);
        }})();
    </script>
    <!-- 左侧播放列表 -->
    <div class="playlist-panel" id="playlistPanel">
        <div class="playlist-header">
            <h1>🎧 播客播放器</h1>
            <div class="stats" id="playlistStats">加载中...</div>
        </div>
        <div class="playlist-search">
            <input type="text" id="searchInput" placeholder="搜索播客..." oninput="filterPlaylist()">
        </div>
        <div class="playlist-items" id="playlistItems">
            <div class="empty-state"><div class="icon">⏳</div>加载中...</div>
        </div>
    </div>

    <!-- 侧边栏收起/展开按钮 -->
    <button class="sidebar-toggle" id="sidebarToggle" onclick="toggleSidebar()" title="收起/展开播放列表">◀</button>

    <!-- 右侧播放器 -->
    <div class="player-panel">
        <div class="player-top-bar">
            <a href="/">← 仪表盘</a>
            <span class="player-title" id="playerTitle">GitHub Trending Audio Player</span>
            <div class="theme-switcher" id="themeSwitcher" style="margin-left:auto;">
                <button class="theme-dot" data-theme="dark" style="background:#0d1117;border-color:#58a6ff" title="Dark"></button>
                <button class="theme-dot" data-theme="light" style="background:#f6f8fa;border-color:#0969da" title="Light"></button>
                <button class="theme-dot" data-theme="midnight" style="background:#0f0f23;border-color:#7c7cff" title="Midnight"></button>
                <button class="theme-dot" data-theme="nord" style="background:#2e3440;border-color:#88c0d0" title="Nord"></button>
            </div>
        </div>

        <div class="player-content" id="playerContent">
            <div class="empty-state">
                <div class="icon">🎵</div>
                <p>从左侧选择一个播客开始播放</p>
            </div>
        </div>

        <div class="bottom-bar" id="bottomBar" style="display:none;">
            <div class="speed-control">
                <label>倍速</label>
                <select id="speedSelect" onchange="changeSpeed(this.value)">
                    <option value="0.75">0.75x</option>
                    <option value="1.0" selected>1.0x</option>
                    <option value="1.25">1.25x</option>
                    <option value="1.5">1.5x</option>
                    <option value="2.0">2.0x</option>
                </select>
            </div>
            <div class="volume-control">
                <span style="font-size:14px; color:var(--text-dim);">🔊</span>
                <input type="range" id="volumeSlider" min="0" max="100" value="80"
                       oninput="changeVolume(this.value)">
            </div>
            <a class="download-btn" id="downloadBtn" href="#" download>
                ⬇ 下载音频
            </a>
        </div>
    </div>

    <script>
        // ── 多主题管理 ──
        function initTheme() {{
            var current = localStorage.getItem('gh-audio-theme') || 'dark';
            document.body.setAttribute('data-theme', current);
            document.querySelectorAll('.theme-dot').forEach(function(dot) {{
                dot.classList.toggle('active', dot.dataset.theme === current);
            }});
        }}
        function setTheme(theme) {{
            localStorage.setItem('gh-audio-theme', theme);
            document.body.setAttribute('data-theme', theme);
            document.querySelectorAll('.theme-dot').forEach(function(dot) {{
                dot.classList.toggle('active', dot.dataset.theme === theme);
            }});
            try {{ new BroadcastChannel('gh-audio-theme').postMessage(theme); }} catch(e) {{}}
        }}
        document.querySelectorAll('.theme-dot').forEach(function(dot) {{
            dot.addEventListener('click', function() {{ setTheme(dot.dataset.theme); }});
        }});
        try {{
            new BroadcastChannel('gh-audio-theme').onmessage = function(e) {{
                if (e.data) {{
                    document.body.setAttribute('data-theme', e.data);
                    document.querySelectorAll('.theme-dot').forEach(function(dot) {{
                        dot.classList.toggle('active', dot.dataset.theme === e.data);
                    }});
                }}
            }};
        }} catch(e) {{}}
        initTheme();

        var allTracks = [];
        var currentTrack = null;
        var currentIdx = -1;
        var howl = null;
        var wavesurfer = null;
        var isSeeking = false;

        // ── 加载播放列表 ──
        function loadPlaylist() {{
            fetch('/api/projects')
                .then(r => r.json())
                .then(data => {{
                    allTracks = data.projects.filter(p => p.has_audio);
                    document.getElementById('playlistStats').textContent =
                        allTracks.length + ' 个播客';
                    renderPlaylist(allTracks);
                    // 如果 URL 有指定项目，自动播放
                    var params = new URLSearchParams(window.location.search);
                    var autoPlay = params.get('play');
                    if (autoPlay) {{
                        var track = allTracks.find(t =>
                            t.name === autoPlay || t.name.replace('_', '/') === autoPlay
                        );
                        if (track) playTrack(track);
                    }}
                }})
                .catch(err => {{
                    document.getElementById('playlistItems').innerHTML =
                        '<div class="empty-state"><div class="icon">❌</div>加载失败</div>';
                }});
        }}

        // 不同曲目的封面渐变色
        var COVER_GRADIENTS = [
            'linear-gradient(135deg, #58a6ff, #bc8cff)',
            'linear-gradient(135deg, #3fb950, #58a6ff)',
            'linear-gradient(135deg, #f85149, #d29922)',
            'linear-gradient(135deg, #bc8cff, #f85149)',
            'linear-gradient(135deg, #d29922, #3fb950)',
            'linear-gradient(135deg, #58a6ff, #3fb950)',
            'linear-gradient(135deg, #bc8cff, #58a6ff)',
            'linear-gradient(135deg, #f85149, #bc8cff)',
        ];

        function renderPlaylist(tracks) {{
            var container = document.getElementById('playlistItems');
            if (tracks.length === 0) {{
                container.innerHTML = '<div class="empty-state"><div class="icon">📭</div><div>暂无播客</div><div class="empty-hint">去仪表盘生成项目吧</div></div>';
                return;
            }}
            container.innerHTML = tracks.map(function(t) {{
                var actualIdx = allTracks.indexOf(t);
                var isActive = currentIdx >= 0 && actualIdx === currentIdx;
                var dur = formatDuration(t.audio_duration);
                var gradIdx = actualIdx % COVER_GRADIENTS.length;
                var coverStyle = 'style="background:' + COVER_GRADIENTS[gradIdx] + '"';
                var coverContent;
                if (isActive && howl && howl.playing()) {{
                    coverContent = '<span class="now-playing-icon"><span class="bar" style="height:8px"></span><span class="bar" style="height:12px"></span><span class="bar" style="height:6px"></span></span>';
                }} else {{
                    coverContent = '<span class="track-number">' + (actualIdx + 1) + '</span>';
                }}
                return '<div class="track-item' + (isActive ? ' active' : '') + '" onclick="playTrack(allTracks[' + actualIdx + '])">' +
                    '<div class="track-cover" ' + coverStyle + '>' + coverContent + '</div>' +
                    '<div class="track-info">' +
                        '<div class="track-name">' + escapeHtml(t.name.replace('_', '/')) + '</div>' +
                        '<div class="track-meta">' +
                            (t.language ? '<span>' + escapeHtml(t.language) + '</span>' : '') +
                            (t.stars ? '<span>⭐' + t.stars + '</span>' : '') +
                        '</div>' +
                    '</div>' +
                    '<div class="track-duration">' + dur + '</div>' +
                '</div>';
            }}).join('');
        }}

        function filterPlaylist() {{
            var q = document.getElementById('searchInput').value.toLowerCase();
            var filtered = allTracks.filter(function(t) {{
                return t.name.toLowerCase().includes(q) ||
                       (t.description && t.description.toLowerCase().includes(q));
            }});
            renderPlaylist(filtered);
        }}

        // ── 播放控制 ──
        function playTrack(track) {{
            currentIdx = allTracks.indexOf(track);
            currentTrack = track;

            // 销毁旧的
            if (howl) {{ howl.unload(); howl = null; }}
            if (wavesurfer) {{ wavesurfer.destroy(); wavesurfer = null; }}

            var audioUrl = '/file/' + track.audio_path;

            // Howler 音频
            howl = new Howl({{
                src: [audioUrl],
                format: ['mp3'],
                html5: true,
                onplay: function() {{
                    updatePlayButton(true);
                    document.querySelector('.cover-art').classList.add('playing');
                    requestAnimationFrame(updateProgress);
                    broadcastState({{ type: 'playing', track: track.name }});
                }},
                onpause: function() {{
                    updatePlayButton(false);
                    document.querySelector('.cover-art').classList.remove('playing');
                    broadcastState({{ type: 'paused', track: track.name }});
                }},
                onend: function() {{
                    updatePlayButton(false);
                    document.querySelector('.cover-art').classList.remove('playing');
                    broadcastState({{ type: 'ended', track: track.name }});
                    playNext();
                }},
                onload: function() {{
                    // 加载波形
                    if (wavesurfer) wavesurfer.load(audioUrl);
                }},
            }});

            // 渲染播放器界面
            renderPlayer(track, audioUrl);

            // 自动播放
            howl.play();
            renderPlaylist(allTracks);
        }}

        function renderPlayer(track, audioUrl) {{
            document.getElementById('playerTitle').textContent = track.name.replace('_', '/');
            document.getElementById('bottomBar').style.display = 'flex';
            document.getElementById('downloadBtn').href = audioUrl;

            var content = document.getElementById('playerContent');
            var desc = track.description ? escapeHtml(track.description.substring(0, 80)) : 'GitHub 开源项目播客';
            var langLabel = track.language ? '<span style="margin-left:8px;padding:2px 8px;background:var(--card-bg);border-radius:4px;font-size:12px;">' + escapeHtml(track.language) + '</span>' : '';
            var gradIdx = currentIdx % COVER_GRADIENTS.length;
            var coverGrad = COVER_GRADIENTS[gradIdx];

            // 读取脚本
            var scriptUrl = track.script_path ? '/file/' + track.script_path : null;

            content.innerHTML =
                '<div class="cover-section">' +
                    '<div class="cover-art" style="background:' + coverGrad + '"><span class="cover-emoji">🎙️</span></div>' +
                    '<div class="cover-info">' +
                        '<h2>' + escapeHtml(track.name.replace('_', '/')) + '</h2>' +
                        '<div class="subtitle">' + desc + langLabel + '</div>' +
                    '</div>' +
                '</div>' +
                '<div class="waveform-container">' +
                    '<div id="waveform"></div>' +
                '</div>' +
                '<div class="controls">' +
                    '<button class="ctrl-btn" onclick="playPrev()" title="上一首">⏮</button>' +
                    '<button class="ctrl-btn play-btn" id="playBtn" onclick="togglePlay()" title="播放/暂停">▶</button>' +
                    '<button class="ctrl-btn" onclick="playNext()" title="下一首">⏭</button>' +
                '</div>' +
                '<div class="progress-section">' +
                    '<span class="time-display" id="currentTime">0:00</span>' +
                    '<div class="progress-bar-wrap" id="progressBar" onclick="seekTo(event)">' +
                        '<div class="progress-fill" id="progressFill"></div>' +
                    '</div>' +
                    '<span class="time-display" id="totalTime">0:00</span>' +
                '</div>' +
                (scriptUrl
                    ? '<details class="script-section"><summary>📋 查看对话脚本</summary>' +
                      '<div class="script-content" id="scriptContent">加载中...</div></details>'
                    : '');

            // 初始化 WaveSurfer
            setTimeout(function() {{
                var wsEl = document.getElementById('waveform');
                if (!wsEl) return;
                // 根据当前主题获取波形颜色
                var theme = document.body.getAttribute('data-theme') || 'dark';
                var waveColors = {{
                    dark: {{ wave: '#30363d', progress: '#58a6ff', cursor: '#bc8cff' }},
                    light: {{ wave: '#d0d7de', progress: '#0969da', cursor: '#8250df' }},
                    midnight: {{ wave: '#3a3a6e', progress: '#7c7cff', cursor: '#c084fc' }},
                    nord: {{ wave: '#4c566a', progress: '#88c0d0', cursor: '#b48ead' }}
                }};
                var wc = waveColors[theme] || waveColors.dark;
                wavesurfer = WaveSurfer.create({{
                    container: '#waveform',
                    waveColor: wc.wave,
                    progressColor: wc.progress,
                    cursorColor: wc.cursor,
                    barWidth: 2,
                    barRadius: 1,
                    barGap: 2,
                    height: 60,
                    responsive: true,
                    normalize: true,
                }});
                wavesurfer.load(audioUrl);
                wavesurfer.on('interaction', function(newTime) {{
                    if (howl) {{
                        howl.seek(newTime);
                    }}
                }});
            }}, 50);

            // 加载脚本
            if (scriptUrl) {{
                fetch(scriptUrl).then(r => r.text()).then(text => {{
                    var el = document.getElementById('scriptContent');
                    if (el) el.textContent = text;
                }}).catch(function() {{}});
            }}

            // 设置总时长
            howl.once('load', function() {{
                var dur = howl.duration();
                document.getElementById('totalTime').textContent = formatTime(dur);
            }});
        }}

        function togglePlay() {{
            if (!howl) return;
            if (howl.playing()) {{
                howl.pause();
            }} else {{
                howl.play();
            }}
        }}

        function updatePlayButton(playing) {{
            var btn = document.getElementById('playBtn');
            if (btn) btn.innerHTML = playing ? '⏸' : '▶';
        }}

        function playNext() {{
            if (currentIdx < 0 || currentIdx >= allTracks.length - 1) return;
            playTrack(allTracks[currentIdx + 1]);
        }}

        function playPrev() {{
            if (currentIdx <= 0) return;
            playTrack(allTracks[currentIdx - 1]);
        }}

        function updateProgress() {{
            if (!howl || !howl.playing()) return;
            var seek = howl.seek();
            var dur = howl.duration();
            var pct = (seek / dur) * 100;
            var fill = document.getElementById('progressFill');
            var cur = document.getElementById('currentTime');
            if (fill) fill.style.width = pct + '%';
            if (cur) cur.textContent = formatTime(seek);
            // 同步波形
            if (wavesurfer) {{
                try {{ wavesurfer.setVolume(0); }} catch(e) {{}}
            }}
            requestAnimationFrame(updateProgress);
        }}

        function seekTo(event) {{
            if (!howl) return;
            var bar = document.getElementById('progressBar');
            var rect = bar.getBoundingClientRect();
            var pct = (event.clientX - rect.left) / rect.width;
            var dur = howl.duration();
            howl.seek(dur * pct);
            if (!howl.playing()) {{
                var fill = document.getElementById('progressFill');
                var cur = document.getElementById('currentTime');
                if (fill) fill.style.width = (pct * 100) + '%';
                if (cur) cur.textContent = formatTime(dur * pct);
            }}
        }}

        function changeSpeed(speed) {{
            if (howl) howl.rate(parseFloat(speed));
        }}

        function changeVolume(val) {{
            if (howl) howl.volume(parseFloat(val) / 100);
        }}

        // ── 工具函数 ──
        function formatDuration(seconds) {{
            if (!seconds || seconds <= 0) return '--:--';
            var m = Math.floor(seconds / 60);
            var s = Math.floor(seconds % 60);
            return m + ':' + (s < 10 ? '0' : '') + s;
        }}

        function formatTime(seconds) {{
            if (!seconds || isNaN(seconds)) return '0:00';
            var m = Math.floor(seconds / 60);
            var s = Math.floor(seconds % 60);
            return m + ':' + (s < 10 ? '0' : '') + s;
        }}

        function escapeHtml(text) {{
            if (!text) return '';
            var div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }}

        // ── 键盘快捷键 ──
        document.addEventListener('keydown', function(e) {{
            if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;
            if (e.code === 'Space') {{ e.preventDefault(); togglePlay(); }}
            else if (e.code === 'ArrowRight' && howl) {{ howl.seek(howl.seek() + 10); }}
            else if (e.code === 'ArrowLeft' && howl) {{ howl.seek(howl.seek() - 10); }}
            else if (e.code === 'KeyN') {{ playNext(); }}
            else if (e.code === 'KeyP') {{ playPrev(); }}
        }});

        // ── 侧边栏收起/展开 ──
        function toggleSidebar() {{
            var panel = document.getElementById('playlistPanel');
            var toggle = document.getElementById('sidebarToggle');
            panel.classList.toggle('collapsed');
            toggle.classList.toggle('collapsed');
            toggle.textContent = panel.classList.contains('collapsed') ? '▶' : '◀';
        }}

        // ── 接收来自主页面的播放指令 ──
        window.addEventListener('message', function(event) {{
            if (!event.data) return;
            var msg = event.data;
            if (msg.type === 'playTrack') {{
                var name = msg.name;
                var track = allTracks.find(function(t) {{
                    return t.name === name || t.name.replace('_', '/') === name;
                }});
                if (track) {{
                    playTrack(track);
                }} else {{
                    // 列表可能还没加载完，等待后重试
                    setTimeout(function() {{
                        track = allTracks.find(function(t) {{
                            return t.name === name || t.name.replace('_', '/') === name;
                        }});
                        if (track) playTrack(track);
                    }}, 1500);
                }}
            }} else if (msg.type === 'togglePlay') {{
                togglePlay();
            }} else if (msg.type === 'next') {{
                playNext();
            }} else if (msg.type === 'prev') {{
                playPrev();
            }} else if (msg.type === 'pause') {{
                if (howl && howl.playing()) howl.pause();
            }}
        }});

        // ── 向主窗口同步播放状态（通过 BroadcastChannel） ──
        var bc = null;
        try {{ bc = new BroadcastChannel('gh-audio-player'); }} catch(e) {{}}
        function broadcastState(state) {{
            if (!bc) return;
            bc.postMessage(state);
        }}

        // 启动
        loadPlaylist();
    </script>
</body>
</html>
"""


PROJECT_HTML = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{name} - 项目详情</title>
    <style>
        /* ═══ 多主题系统 ═══ */
        :root {{ --radius: 12px; --transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1); }}
        [data-theme="dark"] {{
            --bg: #0d1117; --bg-gradient: radial-gradient(ellipse at top, #161b22 0%, #0d1117 60%);
            --card-bg: #161b22; --card-hover: #1c2330;
            --border: #30363d; --border-light: #21262d;
            --text: #e6edf3; --text-dim: #8b949e;
            --accent: #58a6ff; --accent-glow: rgba(88,166,255,0.15);
            --green: #3fb950; --red: #f85149; --yellow: #d29922; --purple: #bc8cff;
            --hover-bg: #1c2128;
            --shadow-sm: 0 2px 8px rgba(0,0,0,0.2); --shadow-md: 0 4px 16px rgba(0,0,0,0.3); --shadow-lg: 0 8px 32px rgba(0,0,0,0.4);
            --header-bg: rgba(22,27,34,0.85); --glass-blur: blur(12px);
        }}
        [data-theme="light"] {{
            --bg: #f6f8fa; --bg-gradient: radial-gradient(ellipse at top, #ffffff 0%, #f6f8fa 60%);
            --card-bg: #ffffff; --card-hover: #f0f3f6;
            --border: #d0d7de; --border-light: #eaeef2;
            --text: #1f2328; --text-dim: #656d76;
            --accent: #0969da; --accent-glow: rgba(9,105,218,0.12);
            --green: #1a7f37; --red: #cf222e; --yellow: #9a6700; --purple: #8250df;
            --hover-bg: #eaeef2;
            --shadow-sm: 0 2px 8px rgba(0,0,0,0.06); --shadow-md: 0 4px 16px rgba(0,0,0,0.1); --shadow-lg: 0 8px 32px rgba(0,0,0,0.12);
            --header-bg: rgba(255,255,255,0.85); --glass-blur: blur(12px);
        }}
        [data-theme="midnight"] {{
            --bg: #0f0f23; --bg-gradient: radial-gradient(ellipse at top, #1a1a3e 0%, #0f0f23 60%);
            --card-bg: #1a1a3e; --card-hover: #252550;
            --border: #3a3a6e; --border-light: #2a2a52;
            --text: #e0e0ff; --text-dim: #8888bb;
            --accent: #7c7cff; --accent-glow: rgba(124,124,255,0.18);
            --green: #50e3a0; --red: #ff6b8a; --yellow: #ffd966; --purple: #c084fc;
            --hover-bg: #252550;
            --shadow-sm: 0 2px 8px rgba(0,0,0,0.3); --shadow-md: 0 4px 16px rgba(0,0,0,0.4); --shadow-lg: 0 8px 32px rgba(0,0,0,0.5);
            --header-bg: rgba(26,26,62,0.85); --glass-blur: blur(12px);
        }}
        [data-theme="nord"] {{
            --bg: #2e3440; --bg-gradient: radial-gradient(ellipse at top, #3b4252 0%, #2e3440 60%);
            --card-bg: #3b4252; --card-hover: #434c5e;
            --border: #4c566a; --border-light: #3f485a;
            --text: #eceff4; --text-dim: #81a1c1;
            --accent: #88c0d0; --accent-glow: rgba(136,192,208,0.15);
            --green: #a3be8c; --red: #bf616a; --yellow: #ebcb8b; --purple: #b48ead;
            --hover-bg: #434c5e;
            --shadow-sm: 0 2px 8px rgba(0,0,0,0.25); --shadow-md: 0 4px 16px rgba(0,0,0,0.35); --shadow-lg: 0 8px 32px rgba(0,0,0,0.45);
            --header-bg: rgba(59,66,82,0.85); --glass-blur: blur(12px);
        }}
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, 'Segoe UI', 'Noto Sans CJK SC', sans-serif;
            background: var(--bg-gradient); color: var(--text); min-height: 100vh;
        }}
        .header {{
            background: var(--card-bg);
            border-bottom: 1px solid var(--border);
            padding: 16px 32px; display: flex; align-items: center; gap: 16px; flex-wrap: wrap;
        }}
        .header a {{ color: var(--accent); text-decoration: none; font-size: 14px; }}
        .header h1 {{ font-size: 18px; word-break: break-all; }}
        .header .header-actions {{ margin-left: auto; display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }}
        .header .btn {{
            background: var(--accent); color: #fff; border: none;
            border-radius: 6px; padding: 8px 16px; font-size: 13px;
            cursor: pointer; text-decoration: none; display: inline-flex; align-items: center; gap: 4px;
        }}
        .header .btn:hover {{ opacity: 0.85; }}
        .header .btn-secondary {{
            background: var(--card-bg); border: 1px solid var(--border); color: var(--text);
        }}
        .header .btn-secondary:hover {{ border-color: var(--accent); }}
        .header .btn-outline {{
            background: var(--card-bg); border: 1px solid var(--border); color: var(--text);
            border-radius: var(--radius); cursor: pointer; white-space: nowrap;
            transition: var(--transition);
        }}
        .header .btn-outline:hover {{ border-color: var(--accent); color: var(--accent); }}
        /* ── README / 文件树弹窗 ── */
        .info-modal-overlay {{
            display: none; position: fixed; inset: 0; z-index: 9998;
            background: rgba(0,0,0,0.6); backdrop-filter: blur(4px);
            justify-content: center; align-items: flex-start; padding: 40px 20px;
            overflow-y: auto;
        }}
        .info-modal-overlay.show {{ display: flex; }}
        .info-modal {{
            background: var(--card-bg); border: 1px solid var(--border);
            border-radius: 14px; width: 100%; max-width: 900px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.5); overflow: hidden;
            display: flex; flex-direction: column; max-height: 85vh;
        }}
        .info-modal-header {{
            display: flex; align-items: center; justify-content: space-between;
            padding: 16px 24px; border-bottom: 1px solid var(--border);
            flex-shrink: 0;
        }}
        .info-modal-title {{ font-size: 16px; font-weight: 700; display: flex; align-items: center; gap: 8px; }}
        .info-modal-close {{
            background: none; border: none; color: var(--text-dim);
            font-size: 22px; cursor: pointer; padding: 4px 8px; border-radius: 6px;
        }}
        .info-modal-close:hover {{ color: var(--red); background: rgba(248,81,73,0.1); }}
        .info-modal-body {{
            overflow-y: auto; padding: 24px; flex: 1;
        }}
        .info-modal-loading {{
            text-align: center; padding: 40px; color: var(--text-dim);
        }}
        .info-modal-error {{
            text-align: center; padding: 40px; color: var(--red);
        }}
        .info-modal-body .md-content {{ line-height: 1.7; }}
        /* 文件树弹窗专用 */
        .ft-modal-body {{ display: flex; gap: 0; padding: 0; }}
        .ft-sidebar {{
            width: 280px; min-width: 280px; border-right: 1px solid var(--border);
            overflow-y: auto; padding: 8px 0; font-size: 13px;
        }}
        .ft-main {{
            flex: 1; overflow-y: auto; padding: 16px 20px; min-width: 0;
        }}
        .ft-item {{
            padding: 4px 12px; cursor: pointer; white-space: nowrap;
            overflow: hidden; text-overflow: ellipsis; color: var(--text);
            border-radius: 4px; margin: 0 4px;
        }}
        .ft-item:hover {{ background: var(--hover-bg, rgba(255,255,255,0.06)); }}
        .ft-item.active {{ background: var(--accent-glow); color: var(--accent); }}
        .ft-item.ft-dir {{ font-weight: 600; }}
        .ft-item.ft-dir::before {{ content: '📁 '; }}
        .ft-item.ft-file::before {{ content: '📄 '; }}
        .ft-viewer {{
            background: var(--bg); border: 1px solid var(--border);
            border-radius: 8px; padding: 16px; font-family: 'SF Mono', 'Consolas', monospace;
            font-size: 13px; line-height: 1.5; white-space: pre-wrap;
            word-break: break-all; max-height: 60vh; overflow-y: auto;
        }}
        .ft-viewer-empty {{
            color: var(--text-dim); text-align: center; padding: 60px 20px;
        }}
        .container {{ max-width: 900px; margin: 0 auto; padding: 32px; }}
        /* ── 主题切换器 ── */
        .theme-switcher {{
            display: flex; gap: 6px; align-items: center;
            padding: 4px 8px; border-radius: 20px;
            background: var(--card-bg); border: 1px solid var(--border-light);
        }}
        .theme-dot {{
            width: 16px; height: 16px; border-radius: 50%;
            border: 2px solid var(--border); cursor: pointer;
            transition: transform 0.2s, box-shadow 0.2s; padding: 0;
        }}
        .theme-dot:hover {{ transform: scale(1.2); }}
        .theme-dot.active {{
            transform: scale(1.25);
            box-shadow: 0 0 0 2px var(--accent), 0 0 8px var(--accent-glow);
        }}
        .section {{
            background: var(--card-bg); border: 1px solid var(--border-light);
            border-radius: 12px; padding: 24px; margin-bottom: 24px;
            transition: border-color 0.25s;
        }}
        .section:hover {{ border-color: var(--border); }}
        .section h3 {{ font-size: 16px; margin-bottom: 16px; color: var(--accent); display: flex; align-items: center; gap: 8px; }}
        .section h3 .section-actions {{ margin-left: auto; display: flex; gap: 6px; }}
        .section h3 .mini-btn {{
            background: var(--bg); border: 1px solid var(--border-light); color: var(--text-dim);
            border-radius: 6px; padding: 3px 10px; font-size: 12px; cursor: pointer;
            transition: all 0.2s;
        }}
        .section h3 .mini-btn:hover {{ border-color: var(--accent); color: var(--accent); box-shadow: 0 0 0 2px var(--accent-glow); }}
        .audio-player {{ text-align: center; }}
        .audio-player audio {{ width: 100%; max-width: 600px; }}
        .audio-controls {{ display: flex; justify-content: center; gap: 8px; margin-top: 12px; align-items: center; }}
        .speed-select {{
            background: var(--bg); border: 1px solid var(--border-light); color: var(--text);
            border-radius: 6px; padding: 4px 8px; font-size: 12px; cursor: pointer;
            transition: all 0.2s;
        }}
        .speed-select:hover {{ border-color: var(--accent); }}
        .md-content {{ line-height: 1.7; }}
        .md-content h1, .md-content h2, .md-content h3 {{ margin: 16px 0 8px; color: var(--accent); }}
        .md-toc {{
            background: var(--bg); border: 1px solid var(--border-light);
            border-radius: 8px; padding: 12px 16px; margin-bottom: 16px;
            font-size: 13px; max-height: 300px; overflow-y: auto;
        }}
        .md-toc.hidden {{ display: none; }}
        .md-toc a {{
            display: block; color: var(--text-dim); text-decoration: none;
            padding: 3px 0; transition: color 0.15s;
        }}
        .md-toc a:hover {{ color: var(--accent); }}
        .md-toc a.level-2 {{ padding-left: 16px; }}
        .md-toc a.level-3 {{ padding-left: 32px; font-size: 12px; }}
        .md-content p {{ margin-bottom: 12px; }}
        .md-content table {{ width: 100%; border-collapse: collapse; margin: 12px 0; }}
        .md-content th, .md-content td {{ border: 1px solid var(--border); padding: 8px 12px; text-align: left; }}
        .md-content th {{ background: rgba(88, 166, 255, 0.1); }}
        .md-content code {{ background: rgba(110, 118, 129, 0.2); padding: 2px 6px; border-radius: 4px; font-size: 13px; }}
        .md-content a {{ color: var(--accent); }}
        .md-content blockquote {{ border-left: 3px solid var(--accent); padding-left: 16px; color: var(--text-dim); margin: 12px 0; }}
        .script-text {{
            white-space: pre-wrap; word-break: break-word; font-size: 14px;
            line-height: 1.6; max-height: 500px; overflow-y: auto;
            background: var(--bg); padding: 16px; border-radius: 8px;
        }}
        .copy-toast {{
            position: fixed; bottom: 24px; left: 50%; transform: translateX(-50%);
            background: var(--green); color: #fff; padding: 10px 24px;
            border-radius: 8px; font-size: 14px; opacity: 0;
            transition: opacity 0.3s; z-index: 999; pointer-events: none;
        }}
        .copy-toast.show {{ opacity: 1; }}

        /* ── 项目问答（DeepWiki 式）── */
        .qa-section .qa-messages {{
            display: flex; flex-direction: column; gap: 12px;
            max-height: 420px; overflow-y: auto; padding: 4px 4px 8px;
        }}
        .qa-empty {{ color: var(--text-dim); font-size: 13px; text-align: center; padding: 24px 0; }}
        .qa-bubble {{
            max-width: 80%; padding: 10px 14px; border-radius: 12px;
            font-size: 14px; line-height: 1.6; word-break: break-word;
            white-space: pre-wrap;
        }}
        .qa-bubble.user {{
            align-self: flex-end; background: var(--accent); color: #fff;
            border-bottom-right-radius: 4px;
        }}
        .qa-bubble.ai {{
            align-self: flex-start; background: var(--bg);
            border: 1px solid var(--border); color: var(--text);
            border-bottom-left-radius: 4px;
        }}
        .qa-bubble.error {{
            align-self: flex-start; background: rgba(248,81,73,0.12);
            border: 1px solid var(--border); color: var(--red);
            border-bottom-left-radius: 4px;
        }}
        .qa-bubble.loading {{ color: var(--text-dim); }}
        .qa-typing {{
            display: inline-block; width: 6px; height: 6px; border-radius: 50%;
            background: var(--text-dim); margin: 0 2px; animation: qa-blink 1.2s infinite;
        }}
        .qa-typing:nth-child(2) {{ animation-delay: 0.2s; }}
        .qa-typing:nth-child(3) {{ animation-delay: 0.4s; }}
        @keyframes qa-blink {{ 0%,100% {{ opacity: 0.2; }} 50% {{ opacity: 1; }} }}
        .qa-input-row {{ display: flex; gap: 8px; margin-top: 16px; }}
        .qa-input {{
            flex: 1; background: var(--bg); border: 1px solid var(--border);
            color: var(--text); border-radius: 8px; padding: 10px 14px; font-size: 14px;
        }}
        .qa-input:focus {{ outline: none; border-color: var(--accent); }}
        .qa-input:disabled {{ opacity: 0.6; }}
        .qa-send {{
            background: var(--accent); color: #fff; border: none;
            border-radius: 8px; padding: 10px 22px; font-size: 14px; cursor: pointer;
        }}
        .qa-send:hover {{ opacity: 0.85; }}
        .qa-send:disabled {{ opacity: 0.5; cursor: not-allowed; }}

        /* ── 代码结构浏览器（CodeFlow / Greptile 式）── */
        .filetree-section .tree-hint {{ font-size: 12px; color: var(--text-dim); font-weight: normal; }}
        .filetree-wrap {{
            display: flex; gap: 16px; align-items: flex-start; flex-wrap: wrap;
        }}
        .filetree-container {{
            flex: 1 1 320px; min-width: 280px; max-width: 100%;
            max-height: 500px; overflow-y: auto;
            background: var(--bg); border: 1px solid var(--border);
            border-radius: 8px; padding: 10px; font-size: 13px;
        }}
        .filetree-container .tree-list {{ list-style: none; padding-left: 0; margin: 0; }}
        .tree-node .tree-children {{ padding-left: 18px; }}
        .tree-node .tree-children .tree-list {{ padding-left: 0; }}
        .tree-row {{
            display: flex; align-items: center; gap: 4px;
            padding: 3px 6px; border-radius: 4px; cursor: pointer;
            user-select: none; white-space: nowrap; transition: background 0.12s;
        }}
        .tree-row:hover {{ background: #1c2128; }}
        .tree-row.active {{ background: rgba(88,166,255,0.18); }}
        .tree-toggle {{ width: 12px; color: var(--text-dim); font-size: 11px; flex-shrink: 0; }}
        .tree-icon {{ width: 16px; text-align: center; flex-shrink: 0; }}
        .tree-name {{ flex: 1; overflow: hidden; text-overflow: ellipsis; }}
        .tree-size {{ color: var(--text-dim); font-size: 11px; flex-shrink: 0; }}
        .tree-folder .tree-name {{ font-weight: 600; }}
        .tree-file .tree-name {{ color: var(--text); }}
        .tree-loading, .tree-error, .tree-note {{
            padding: 12px; font-size: 13px; color: var(--text-dim);
        }}
        .tree-error {{ color: #f85149; }}
        .tree-note {{ border-top: 1px solid var(--border); margin-top: 8px; }}
        .file-viewer {{
            display: none; flex: 1 1 380px; min-width: 320px;
            background: var(--bg); border: 1px solid var(--border);
            border-radius: 8px; overflow: hidden;
        }}
        .file-header {{
            display: flex; justify-content: space-between; align-items: center; gap: 12px;
            padding: 8px 12px; background: var(--card-bg);
            border-bottom: 1px solid var(--border); font-size: 12px;
        }}
        .file-header .file-path {{ color: var(--accent); word-break: break-all; }}
        .file-header .file-size {{ color: var(--text-dim); flex-shrink: 0; }}
        .file-viewer pre.file-content {{
            margin: 0; padding: 14px; max-height: 460px; overflow: auto;
            font-size: 13px; line-height: 1.55; white-space: pre-wrap; word-break: break-word;
        }}
        .file-viewer code {{
            font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace;
        }}

        /* ── 代码搜索（Greptile 式自然语言代码搜索）── */
        .codesearch-section .cs-hint {{
            color: var(--text-dim); font-size: 13px; margin-bottom: 12px; line-height: 1.6;
        }}
        .codesearch-section .search-input-row {{
            display: flex; gap: 8px; margin-bottom: 12px;
        }}
        .codesearch-section .search-input {{
            flex: 1; background: var(--bg); border: 1px solid var(--border);
            color: var(--text); border-radius: 8px; padding: 10px 14px; font-size: 14px;
        }}
        .codesearch-section .search-input:focus {{ outline: none; border-color: var(--accent); }}
        .codesearch-section .search-input:disabled {{ opacity: 0.6; }}
        .codesearch-section .search-btn {{
            background: var(--accent); color: #fff; border: none;
            border-radius: 8px; padding: 10px 20px; font-size: 14px; cursor: pointer; white-space: nowrap;
        }}
        .codesearch-section .search-btn:hover {{ opacity: 0.85; }}
        .codesearch-section .search-btn:disabled {{ opacity: 0.5; cursor: not-allowed; }}
        .codesearch-section .quick-tags {{
            display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 12px;
        }}
        .codesearch-section .quick-tag {{
            background: var(--bg); border: 1px solid var(--border); color: var(--text-dim);
            border-radius: 14px; padding: 4px 12px; font-size: 12px; cursor: pointer;
            transition: border-color 0.15s, color 0.15s; user-select: none;
        }}
        .codesearch-section .quick-tag:hover {{ border-color: var(--accent); color: var(--accent); }}
        .codesearch-section .search-meta {{
            display: flex; gap: 12px; align-items: center; flex-wrap: wrap;
            font-size: 12px; color: var(--text-dim); margin-bottom: 8px;
        }}
        .codesearch-section .search-meta b {{ color: var(--text); }}
        .codesearch-section .search-source {{
            background: rgba(88,166,255,0.12); color: var(--accent);
            border-radius: 4px; padding: 1px 8px;
        }}
        .codesearch-section .search-results {{
            max-height: 400px; overflow-y: auto; display: flex; flex-direction: column; gap: 8px;
        }}
        .codesearch-section .search-result {{
            background: var(--bg); border: 1px solid var(--border); border-radius: 8px;
            padding: 10px 14px; cursor: pointer; transition: border-color 0.15s;
        }}
        .codesearch-section .search-result:hover {{ border-color: var(--accent); }}
        .codesearch-section .search-head {{
            display: flex; align-items: center; gap: 8px; margin-bottom: 6px; font-size: 13px;
        }}
        .codesearch-section .search-path {{ color: var(--accent); word-break: break-all; }}
        .codesearch-section .search-line {{ color: var(--text-dim); }}
        .codesearch-section .search-score {{ margin-left: auto; color: var(--text-dim); font-size: 12px; flex-shrink: 0; }}
        .codesearch-section .search-link {{ color: var(--text-dim); text-decoration: none; flex-shrink: 0; }}
        .codesearch-section .search-link:hover {{ color: var(--accent); }}
        .codesearch-section .match-type {{
            background: rgba(63,185,80,0.15); color: var(--green);
            border-radius: 4px; padding: 1px 8px; font-size: 11px; text-transform: uppercase;
            flex-shrink: 0;
        }}
        .codesearch-section .search-snippet {{
            margin: 0; white-space: pre-wrap; word-break: break-word; font-size: 13px;
            line-height: 1.55; color: var(--text); max-height: 4.5em; overflow: hidden;
        }}
        .codesearch-section .search-result.expanded .search-snippet {{ max-height: none; }}
        .codesearch-section .search-snippet mark {{
            background: rgba(187,128,9,0.4); color: #fff; border-radius: 2px; padding: 0 2px;
        }}
        .codesearch-section .search-empty, .codesearch-section .search-loading {{
            color: var(--text-dim); font-size: 13px; text-align: center; padding: 24px 0;
        }}
        .codesearch-section .search-empty.error {{ color: #f85149; }}

        /* ── 社区洞察（借鉴 Zread.ai 社区讨论摘要）── */
        .community-section .community-loading {{
            color: var(--text-dim); font-size: 13px; text-align: center; padding: 24px 0;
        }}
        .community-section .community-error {{
            color: #f85149; font-size: 13px; text-align: center; padding: 24px 0;
        }}
        .community-section .ci-subhead {{
            font-size: 13px; color: var(--text-dim); margin: 20px 0 10px; font-weight: 600;
        }}
        .community-section .ci-subhead:first-of-type {{ margin-top: 0; }}
        /* 基本信息卡片行 */
        .ci-stats-row {{
            display: flex; flex-wrap: wrap; gap: 12px;
        }}
        .ci-stat-card {{
            flex: 1 1 140px; background: var(--bg); border: 1px solid var(--border);
            border-radius: 8px; padding: 12px 16px; display: flex; align-items: center; gap: 10px;
        }}
        .ci-stat-card .ci-stat-icon {{ font-size: 20px; flex-shrink: 0; }}
        .ci-stat-card .ci-stat-body {{ display: flex; flex-direction: column; }}
        .ci-stat-card .ci-stat-value {{
            font-size: 18px; font-weight: 700; color: var(--text); line-height: 1.2;
        }}
        .ci-stat-card .ci-stat-label {{
            font-size: 12px; color: var(--text-dim); margin-top: 2px;
        }}
        .ci-topics {{ display: flex; flex-wrap: wrap; gap: 6px; margin-top: 4px; }}
        .ci-topic {{
            background: rgba(88,166,255,0.12); color: var(--accent);
            border: 1px solid rgba(88,166,255,0.25); border-radius: 14px;
            padding: 3px 12px; font-size: 12px;
        }}
        .ci-no-topics {{ color: var(--text-dim); font-size: 13px; }}
        /* 通用列表项 */
        .ci-list {{ display: flex; flex-direction: column; gap: 8px; }}
        .ci-item {{
            background: var(--bg); border: 1px solid var(--border); border-radius: 8px;
            padding: 10px 14px; text-decoration: none; color: var(--text);
            transition: border-color 0.15s; display: block;
        }}
        .ci-item:hover {{ border-color: var(--accent); }}
        .ci-item-head {{
            display: flex; align-items: center; gap: 8px; flex-wrap: wrap;
        }}
        .ci-item-title {{ font-size: 14px; flex: 1; min-width: 0; word-break: break-word; }}
        .ci-item-num {{
            font-size: 12px; color: var(--text-dim); flex-shrink: 0;
            background: var(--card-bg); border: 1px solid var(--border);
            border-radius: 4px; padding: 1px 7px;
        }}
        .ci-comments {{
            font-size: 12px; color: var(--text-dim); flex-shrink: 0;
            display: inline-flex; align-items: center; gap: 3px;
        }}
        .ci-labels {{ display: flex; flex-wrap: wrap; gap: 5px; margin-top: 6px; }}
        .ci-label {{
            font-size: 11px; border-radius: 10px; padding: 1px 9px;
            border: 1px solid var(--border); color: var(--text-dim);
        }}
        .ci-meta {{ font-size: 12px; color: var(--text-dim); margin-top: 4px; }}
        /* 贡献者横向排列 */
        .ci-contributors {{
            display: flex; flex-wrap: wrap; gap: 14px;
        }}
        .ci-contributor {{
            display: flex; flex-direction: column; align-items: center; gap: 6px;
            text-decoration: none; width: 78px; text-align: center;
        }}
        .ci-contributor img {{
            width: 48px; height: 48px; border-radius: 50%;
            border: 2px solid var(--border); object-fit: cover;
        }}
        .ci-contributor:hover img {{ border-color: var(--accent); }}
        .ci-contributor .ci-login {{
            font-size: 12px; color: var(--accent); word-break: break-all; line-height: 1.2;
        }}
        .ci-contributor .ci-contribs {{
            font-size: 11px; color: var(--text-dim);
        }}
        .ci-empty {{ color: var(--text-dim); font-size: 13px; padding: 8px 0; }}

        /* ── 入门指南（Zread.ai 式受众定制）── */
        .onboarding-tabs {{
            display: flex; gap: 8px; margin-bottom: 16px; flex-wrap: wrap;
        }}
        .onboarding-tab {{
            background: var(--bg); border: 1px solid var(--border); color: var(--text-dim);
            padding: 8px 18px; border-radius: 8px; cursor: pointer; font-size: 14px;
            transition: border-color 0.15s, color 0.15s, background 0.15s;
            display: inline-flex; align-items: center; gap: 6px;
        }}
        .onboarding-tab:hover {{ border-color: var(--accent); color: var(--text); }}
        .onboarding-tab.active {{
            background: var(--accent); color: #fff; border-color: var(--accent);
        }}
        .onboarding-content {{
            min-height: 120px; background: var(--bg); border: 1px solid var(--border);
            border-radius: 8px; padding: 18px 22px;
        }}
        .onboarding-content .md-content h1:first-child {{ margin-top: 0; }}
        .onboarding-empty {{
            color: var(--text-dim); font-size: 14px; text-align: center; padding: 36px 0;
        }}
        .onboarding-error {{
            color: #f85149; font-size: 14px; text-align: center; padding: 24px 0;
            white-space: pre-wrap; word-break: break-word;
        }}
        .onboarding-loading {{
            display: flex; align-items: center; justify-content: center; gap: 10px;
            padding: 36px 0; color: var(--text-dim); font-size: 14px;
        }}
        .onboarding-spinner {{
            width: 18px; height: 18px; border: 2px solid var(--border);
            border-top-color: var(--accent); border-radius: 50%;
            animation: ob-spin 0.8s linear infinite; flex-shrink: 0;
        }}
        @keyframes ob-spin {{ to {{ transform: rotate(360deg); }} }}
    </style>
    <script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/highlightjs/cdn-release@11.10.0/build/styles/github-dark.min.css">
    <script src="https://cdn.jsdelivr.net/gh/highlightjs/cdn-release@11.10.0/build/highlight.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
</head>
<body data-theme="dark">
    <script>
        (function() {{
            var t = localStorage.getItem('gh-audio-theme') || 'dark';
            document.body.setAttribute('data-theme', t);
        }})();
    </script>
    <div class="header">
        <a href="/">← 返回仪表盘</a>
        <h1>{name}</h1>
        <div class="header-actions">
            <div class="theme-switcher">
                <button class="theme-dot" data-theme="dark" style="background:#0d1117;border-color:#58a6ff" title="Dark"></button>
                <button class="theme-dot" data-theme="light" style="background:#f6f8fa;border-color:#0969da" title="Light"></button>
                <button class="theme-dot" data-theme="midnight" style="background:#0f0f23;border-color:#7c7cff" title="Midnight"></button>
                <button class="theme-dot" data-theme="nord" style="background:#2e3440;border-color:#88c0d0" title="Nord"></button>
            </div>
            <button class="btn btn-outline" onclick="openReadmeModal()" id="readmeBtn" style="font-size:13px; padding:6px 14px;">📖 README</button>
            <button class="btn btn-outline" onclick="openFileTreeModal()" id="fileTreeBtn" style="font-size:13px; padding:6px 14px;">📂 目录</button>
            {download_md_btn}
            {download_audio_btn}
            {download_script_btn}
        </div>
    </div>

    <div class="container">
        {audio_player}

        <div class="section qa-section" data-dir="{qa_dir}" data-project="{qa_project}">
            <h3>💬 项目问答</h3>
            <div class="qa-messages" id="qaMessages">
                <div class="qa-empty">针对此项目提问，AI 将基于项目文档回答你的问题</div>
            </div>
            <div class="qa-input-row">
                <input type="text" class="qa-input" id="qaInput"
                    placeholder="输入你的问题，按 Enter 发送...">
                <button class="qa-send" id="qaSend" onclick="sendQuestion()">发送</button>
            </div>
        </div>

        <div class="section">
            <h3>
                📄 项目文档
                <span class="section-actions">
                    <button class="mini-btn" onclick="toggleToc()">📑 目录</button>
                    <button class="mini-btn" onclick="copyText('md')">📋 复制</button>
                </span>
            </h3>
            <div class="md-toc hidden" id="mdToc"></div>
            <div class="md-content">{md_html}</div>
        </div>

        <div class="section codesearch-section" id="codeSearchSection"
             data-repo="{repo_full}" data-language="{proj_language}">
            <h3>🔍 代码搜索
                <span class="section-actions">
                    <span class="search-meta-inline" id="codeSearchMetaInline" style="font-size:12px;color:var(--text-dim);font-weight:normal;"></span>
                </span>
            </h3>
            <p class="cs-hint">用自然语言或代码模式搜索项目源码（如：认证、数据库连接、API 路由、<code>def</code>、<code>class</code>）。点击结果可展开查看完整上下文。</p>
            <div class="search-input-row">
                <input type="text" class="search-input" id="codeSearchInput"
                    placeholder="搜索代码...（如：认证、数据库连接、API 路由）">
                <button class="search-btn" id="codeSearchBtn" onclick="runCodeSearch()">搜索</button>
            </div>
            <div class="quick-tags">
                <span class="quick-tag" data-query="def ">函数定义</span>
                <span class="quick-tag" data-query="class ">类定义</span>
                <span class="quick-tag" data-query="route|app.get|app.post|app.route|router">API 路由</span>
                <span class="quick-tag" data-query="config|settings|CONFIG|Config">配置项</span>
                <span class="quick-tag" data-query="import |from |require|use |#include">导入语句</span>
                <span class="quick-tag" data-query="TODO|FIXME|HACK|XXX">待办标记</span>
            </div>
            <div class="search-meta" id="codeSearchMeta"></div>
            <div class="search-results" id="codeSearchResults">
                <div class="search-empty">输入关键词或点击快捷标签开始搜索代码</div>
            </div>
        </div>

        <div class="section onboarding-section" id="onboardingSection" data-dir="{qa_dir}" data-project="{qa_project}">
            <h3>📖 入门指南
                <span class="section-actions">
                    <span class="onboarding-hint">选择受众，AI 生成专属指南</span>
                </span>
            </h3>
            <div class="onboarding-tabs">
                <button class="onboarding-tab" data-audience="beginner">🌱 新手</button>
                <button class="onboarding-tab" data-audience="developer">👨‍💻 开发者</button>
                <button class="onboarding-tab" data-audience="architect">🏗️ 架构师</button>
            </div>
            <div class="onboarding-content" id="onboardingContent">
                <div class="onboarding-empty">点击上方标签，AI 将为该受众生成专属入门指南（首次加载需调用 LLM，请稍候）</div>
            </div>
        </div>

        <div class="section community-section" id="communitySection" data-repo="{repo_full}">
            <h3>👥 社区洞察
                <span class="section-actions">
                    <span id="communityMetaInline" style="font-size:12px;color:var(--text-dim);font-weight:normal;"></span>
                </span>
            </h3>
            <div id="communityBody">
                <div class="community-loading">⏳ 正在加载社区洞察…</div>
            </div>
        </div>

        <div class="section filetree-section">
            <h3>
                📂 代码结构
                <span class="section-actions">
                    <span class="tree-hint">点击文件查看内容</span>
                </span>
            </h3>
            <div class="filetree-wrap" id="filetreeSection" data-repo="{repo_full}">
                <div class="filetree-container" id="filetreeContainer">
                    <div class="tree-loading">⏳ 正在加载文件结构...</div>
                </div>
                <div class="file-viewer" id="fileViewer"></div>
            </div>
        </div>

        {script_display}
    </div>

    <div class="copy-toast" id="toast">已复制到剪贴板</div>

    <!-- README 弹窗 -->
    <div class="info-modal-overlay" id="readmeModalOverlay" onclick="if(event.target===this)closeReadmeModal()">
        <div class="info-modal">
            <div class="info-modal-header">
                <div class="info-modal-title">📖 README 原文</div>
                <div style="display:flex; align-items:center; gap:8px;">
                    <a id="readmeGhLink" href="#" target="_blank" style="font-size:12px; color:var(--accent); text-decoration:none;">在 GitHub 查看 →</a>
                    <button class="info-modal-close" onclick="closeReadmeModal()">✕</button>
                </div>
            </div>
            <div class="info-modal-body" id="readmeModalBody">
                <div class="info-modal-loading">⏳ 正在从 GitHub 获取 README...</div>
            </div>
        </div>
    </div>

    <!-- 文件目录弹窗 -->
    <div class="info-modal-overlay" id="ftModalOverlay" onclick="if(event.target===this)closeFileTreeModal()">
        <div class="info-modal" style="max-width: 1100px;">
            <div class="info-modal-header">
                <div class="info-modal-title">📂 文件目录</div>
                <div style="display:flex; align-items:center; gap:8px;">
                    <span id="ftRepoName" style="font-size:12px; color:var(--text-dim);"></span>
                    <button class="info-modal-close" onclick="closeFileTreeModal()">✕</button>
                </div>
            </div>
            <div class="info-modal-body ft-modal-body">
                <div class="ft-sidebar" id="ftSidebar">
                    <div class="info-modal-loading">⏳ 正在加载文件结构...</div>
                </div>
                <div class="ft-main">
                    <div class="ft-viewer-empty" id="ftViewer">
                        👈 点击左侧文件查看内容
                    </div>
                </div>
            </div>
        </div>
    </div>

    <!-- 用 text/plain 标签安全存储大段文本，避免模板字符串中反引号冲突 -->
    <script type="text/plain" id="scriptTextData">{script_raw}</script>
    <script type="text/plain" id="mdTextData">{md_raw}</script>
    <script type="text/plain" id="repoFullData">{repo_full}</script>

    <script>
        // 渲染 Markdown 中的 Mermaid 架构图（由 _markdown_to_html 输出 <div class="mermaid">）
        // Mermaid 主题跟随多主题系统
        function getMermaidTheme() {{
            var t = document.body.getAttribute('data-theme') || 'dark';
            // mermaid 支持: default, dark, forest, neutral, base
            if (t === 'light') return 'default';
            if (t === 'nord') return 'base';
            if (t === 'midnight') return 'dark';
            return 'dark';
        }}
        function initMermaid() {{
            if (window.mermaid) {{
                mermaid.initialize({{ startOnLoad: true, theme: getMermaidTheme(), securityLevel: 'loose' }});
            }}
        }}
        initMermaid();
        // 主题切换时重新渲染 Mermaid
        try {{
            new BroadcastChannel('gh-audio-theme').onmessage = function(e) {{
                if (e.data && window.mermaid) {{
                    mermaid.initialize({{ startOnLoad: false, theme: getMermaidTheme(), securityLevel: 'loose' }});
                    var nodes = document.querySelectorAll('.mermaid');
                    if (nodes.length > 0) {{
                        nodes.forEach(function(n) {{ n.removeAttribute('data-processed'); n.innerHTML = n.textContent; }});
                        mermaid.run({{ nodes: nodes }});
                    }}
                }}
            }};
        }} catch(e) {{}}

        // ── README 弹窗 ──
        var _readmeLoaded = false;
        function openReadmeModal() {{
            if (!REPO_FULL || REPO_FULL.indexOf('/') < 0) {{
                alert('此项目未关联 GitHub 仓库，无法获取 README');
                return;
            }}
            document.getElementById('readmeModalOverlay').classList.add('show');
            if (_readmeLoaded) return;
            fetch('/api/readme?repo=' + encodeURIComponent(REPO_FULL))
                .then(function(r) {{ return r.json(); }})
                .then(function(data) {{
                    if (data.error) {{
                        document.getElementById('readmeModalBody').innerHTML =
                            '<div class="info-modal-error">❌ ' + data.error + '</div>';
                        return;
                    }}
                    var html;
                    if (window.marked && typeof marked.parse === 'function') {{
                        try {{ html = marked.parse(data.content); }}
                        catch(e) {{ html = '<pre>' + data.content.replace(/</g,'&lt;') + '</pre>'; }}
                    }} else {{
                        html = '<pre>' + data.content.replace(/</g,'&lt;') + '</pre>';
                    }}
                    document.getElementById('readmeModalBody').innerHTML =
                        '<div class="md-content">' + html + '</div>';
                    var ghLink = document.getElementById('readmeGhLink');
                    if (data.html_url) ghLink.href = data.html_url;
                    // 代码高亮 + Mermaid 渲染
                    if (window.hljs) {{
                        document.querySelectorAll('#readmeModalBody pre code').forEach(function(el) {{
                            try {{ hljs.highlightElement(el); }} catch(e) {{}}
                        }});
                    }}
                    if (window.mermaid) {{
                        var nodes = document.querySelectorAll('#readmeModalBody .language-mermaid');
                        nodes.forEach(function(code) {{
                            var pre = code.parentElement;
                            if (pre && pre.tagName === 'PRE') {{
                                var div = document.createElement('div');
                                div.className = 'mermaid';
                                div.textContent = code.textContent;
                                pre.parentElement.replaceChild(div, pre);
                            }}
                        }});
                        var mNodes = document.querySelectorAll('#readmeModalBody .mermaid');
                        if (mNodes.length > 0) {{
                            try {{ mermaid.run({{ nodes: mNodes }}); }} catch(e) {{}}
                        }}
                    }}
                    _readmeLoaded = true;
                }})
                .catch(function(e) {{
                    document.getElementById('readmeModalBody').innerHTML =
                        '<div class="info-modal-error">❌ 网络错误：' + e.message + '</div>';
                }});
        }}
        function closeReadmeModal() {{
            document.getElementById('readmeModalOverlay').classList.remove('show');
        }}

        // ── 文件目录弹窗 ──
        var _ftLoaded = false;
        function openFileTreeModal() {{
            if (!REPO_FULL || REPO_FULL.indexOf('/') < 0) {{
                alert('此项目未关联 GitHub 仓库，无法获取文件目录');
                return;
            }}
            document.getElementById('ftModalOverlay').classList.add('show');
            document.getElementById('ftRepoName').textContent = REPO_FULL;
            if (_ftLoaded) return;
            fetch('/api/filetree?repo=' + encodeURIComponent(REPO_FULL))
                .then(function(r) {{ return r.json(); }})
                .then(function(data) {{
                    if (data.error) {{
                        document.getElementById('ftSidebar').innerHTML =
                            '<div class="info-modal-error">❌ ' + data.error + '</div>';
                        return;
                    }}
                    renderFtSidebar(data.tree || []);
                    _ftLoaded = true;
                }})
                .catch(function(e) {{
                    document.getElementById('ftSidebar').innerHTML =
                        '<div class="info-modal-error">❌ 网络错误：' + e.message + '</div>';
                }});
        }}
        function closeFileTreeModal() {{
            document.getElementById('ftModalOverlay').classList.remove('show');
        }}
        function renderFtSidebar(tree) {{
            // 构建嵌套结构
            var dirs = {{}}, files = [];
            tree.forEach(function(item) {{
                var parts = item.path.split('/');
                if (item.type === 'tree') {{
                    dirs[item.path] = true;
                }} else if (item.type === 'blob') {{
                    files.push(item);
                }}
            }});
            // 只显示前 2 层目录 + 顶层文件
            var html = '', shownDirs = {{}}, shownFiles = [];
            tree.forEach(function(item) {{
                var parts = item.path.split('/');
                if (parts.length === 1 && item.type === 'blob') {{
                    shownFiles.push(item);
                }} else if (item.type === 'tree' && parts.length <= 2) {{
                    shownDirs[item.path] = item;
                }}
            }});
            // 渲染目录
            Object.keys(shownDirs).sort().forEach(function(path) {{
                var name = path.split('/').pop();
                var indent = (path.split('/').length - 1) * 16;
                html += '<div class="ft-item ft-dir" style="padding-left:' + (12 + indent) + 'px" onclick="loadFtFile(&quot;' + path + '&quot;,true,event)">' + name + '/</div>';
            }});
            // 渲染顶层文件
            shownFiles.sort(function(a,b) {{ return a.path.localeCompare(b.path); }});
            shownFiles.forEach(function(item) {{
                var icon = getFileIcon(item.path);
                html += '<div class="ft-item ft-file" onclick="loadFtFile(&quot;' + item.path + '&quot;,false,event)">' + icon + ' ' + item.path + '</div>';
            }});
            // 显示更多文件（嵌套）
            var nestedFiles = files.filter(function(f) {{
                return f.path.split('/').length > 1;
            }});
            if (nestedFiles.length > 0) {{
                html += '<div style="padding:8px 12px; margin-top:8px; border-top:1px solid var(--border); font-size:11px; color:var(--text-dim);">嵌套文件 (' + nestedFiles.length + ')</div>';
                // 按目录分组显示
                nestedFiles.slice(0, 200).forEach(function(item) {{
                    var parts = item.path.split('/');
                    var name = parts.pop();
                    var dirPath = parts.join('/');
                    var indent = parts.length * 16;
                    html += '<div class="ft-item ft-file" style="padding-left:' + (12 + indent) + 'px" onclick="loadFtFile(&quot;' + item.path + '&quot;,false,event)" title="' + item.path + '">' + name + '</div>';
                }});
                if (nestedFiles.length > 200) {{
                    html += '<div style="padding:8px 12px; font-size:11px; color:var(--text-dim);">... 还有 ' + (nestedFiles.length - 200) + ' 个文件</div>';
                }}
            }}
            document.getElementById('ftSidebar').innerHTML = html || '<div class="info-modal-error">未找到文件</div>';
        }}
        function getFileIcon(path) {{
            var ext = path.split('.').pop().toLowerCase();
            var icons = {{
                'py':'🐍','js':'📜','ts':'📘','jsx':'⚛️','tsx':'⚛️',
                'json':'📋','md':'📝','txt':'📄','yml':'⚙️','yaml':'⚙️',
                'toml':'⚙️','cfg':'⚙️','ini':'⚙️','html':'🌐','css':'🎨',
                'go':'🐹','rs':'🦀','java':'☕','c':'🔧','cpp':'🔧','h':'🔧',
                'sh':'🔧','bat':'🔧','sql':'🗄️','lock':'🔒','gitignore':'🚫'
            }};
            return icons[ext] || '📄';
        }}
        function loadFtFile(path, isDir, evt) {{
            if (isDir) return;  // 目录暂不展开
            // 高亮选中
            document.querySelectorAll('#ftSidebar .ft-item').forEach(function(el) {{
                el.classList.remove('active');
            }});
            if (evt && evt.target) evt.target.classList.add('active');
            var viewer = document.getElementById('ftViewer');
            viewer.innerHTML = '<div class="info-modal-loading">⏳ 加载中: ' + path + '</div>';
            fetch('/api/file?repo=' + encodeURIComponent(REPO_FULL) + '&path=' + encodeURIComponent(path))
                .then(function(r) {{ return r.json(); }})
                .then(function(data) {{
                    if (data.error) {{
                        viewer.innerHTML = '<div class="info-modal-error">❌ ' + data.error + '</div>';
                        return;
                    }}
                    var content = data.content || '';
                    var escaped = content.replace(/</g,'&lt;').replace(/>/g,'&gt;');
                    viewer.innerHTML = '<div style="margin-bottom:8px; font-size:12px; color:var(--text-dim);">📄 ' + path + '</div><div class="ft-viewer">' + escaped + '</div>';
                    if (window.hljs) {{
                        var codeEl = viewer.querySelector('.ft-viewer');
                        if (codeEl) {{
                            var pre = document.createElement('pre');
                            var code = document.createElement('code');
                            code.textContent = content;
                            var ext = path.split('.').pop();
                            if (ext) code.className = 'language-' + ext;
                            pre.appendChild(code);
                            viewer.querySelector('.ft-viewer').innerHTML = '';
                            viewer.querySelector('.ft-viewer').appendChild(pre);
                            try {{ hljs.highlightElement(code); }} catch(e) {{}}
                        }}
                    }}
                }})
                .catch(function(e) {{
                    viewer.innerHTML = '<div class="info-modal-error">❌ ' + e.message + '</div>';
                }});
        }}

        const REPO_FULL = document.getElementById('repoFullData').textContent;
        const SCRIPT_TEXT = document.getElementById('scriptTextData').textContent;
        const MD_TEXT = document.getElementById('mdTextData').textContent;

        // ── 多主题管理 ──
        function initTheme() {{
            var current = localStorage.getItem('gh-audio-theme') || 'dark';
            document.body.setAttribute('data-theme', current);
            document.querySelectorAll('.theme-dot').forEach(function(dot) {{
                dot.classList.toggle('active', dot.dataset.theme === current);
            }});
        }}
        function setTheme(theme) {{
            localStorage.setItem('gh-audio-theme', theme);
            document.body.setAttribute('data-theme', theme);
            document.querySelectorAll('.theme-dot').forEach(function(dot) {{
                dot.classList.toggle('active', dot.dataset.theme === theme);
            }});
            try {{ new BroadcastChannel('gh-audio-theme').postMessage(theme); }} catch(e) {{}}
        }}
        document.querySelectorAll('.theme-dot').forEach(function(dot) {{
            dot.addEventListener('click', function() {{ setTheme(dot.dataset.theme); }});
        }});
        try {{
            new BroadcastChannel('gh-audio-theme').onmessage = function(e) {{
                if (e.data) {{
                    document.body.setAttribute('data-theme', e.data);
                    document.querySelectorAll('.theme-dot').forEach(function(dot) {{
                        dot.classList.toggle('active', dot.dataset.theme === e.data);
                    }});
                }}
            }};
        }} catch(e) {{}}
        initTheme();

        function copyText(type) {{
            const text = type === 'md' ? MD_TEXT : SCRIPT_TEXT;
            navigator.clipboard.writeText(text).then(() => {{
                const toast = document.getElementById('toast');
                toast.classList.add('show');
                setTimeout(() => toast.classList.remove('show'), 2000);
            }});
        }}

        // ── 文档目录（自动生成锚点）──
        function toggleToc() {{
            var toc = document.getElementById('mdToc');
            if (!toc.classList.contains('hidden')) {{
                toc.classList.add('hidden');
                return;
            }}
            // 生成目录
            var headings = document.querySelectorAll('.md-content h1, .md-content h2, .md-content h3');
            if (headings.length === 0) {{
                toc.innerHTML = '<div style="color:var(--text-dim);">暂无标题</div>';
            }} else {{
                var html = '';
                headings.forEach(function(h, i) {{
                    var id = 'heading-' + i;
                    h.id = id;
                    var level = h.tagName.toLowerCase();
                    var text = h.textContent || '';
                    html += '<a class="level-' + level.replace('h','') + '" href="#' + id + '" onclick="document.getElementById(&quot;mdToc&quot;).classList.add(&quot;hidden&quot;)">' +
                        escapeHtml(text) + '</a>';
                }});
                toc.innerHTML = html;
            }}
            toc.classList.remove('hidden');
        }}

        function changeDetailSpeed(select) {{
            const audio = document.getElementById('detailAudio');
            if (audio) audio.playbackRate = parseFloat(select.value);
        }}

        // ── 入门指南（Zread.ai 式受众定制，懒加载）──
        var onboardingCache = {{}};     // audience -> 原始 Markdown
        var onboardingPending = {{}};   // audience -> 是否正在请求
        var onboardingActive = null;    // 当前选中的受众

        function obEscapeHtml(s) {{
            return String(s).replace(/[&<>]/g, function(c) {{
                return ({{'&':'&amp;','<':'&lt;','>':'&gt;'}})[c];
            }});
        }}

        function obSetTabActive(audience) {{
            onboardingActive = audience;
            var tabs = document.querySelectorAll('.onboarding-tab');
            for (var i = 0; i < tabs.length; i++) {{
                tabs[i].classList.toggle('active', tabs[i].getAttribute('data-audience') === audience);
            }}
        }}

        function obRenderMarkdown(md) {{
            var box = document.getElementById('onboardingContent');
            if (!box) return;
            var html;
            if (window.marked && typeof marked.parse === 'function') {{
                try {{ html = marked.parse(md); }}
                catch (e) {{ html = '<pre>' + obEscapeHtml(md) + '</pre>'; }}
            }} else {{
                html = '<pre>' + obEscapeHtml(md) + '</pre>';
            }}
            box.innerHTML = '<div class="md-content">' + html + '</div>';
            obEnhanceContent(box);
        }}

        function obEnhanceContent(container) {{
            // 1. 把 mermaid 代码块（marked 输出 <code class="language-mermaid">）
            //    转成 <div class="mermaid">，交由 mermaid.js 渲染
            var mermaidCodes = container.querySelectorAll('code.language-mermaid');
            for (var i = 0; i < mermaidCodes.length; i++) {{
                (function(code) {{
                    var pre = code.parentElement;
                    if (!pre || pre.tagName !== 'PRE') return;
                    var div = document.createElement('div');
                    div.className = 'mermaid';
                    div.textContent = code.textContent;
                    pre.parentElement.replaceChild(div, pre);
                }})(mermaidCodes[i]);
            }}
            // 2. 代码高亮
            if (window.hljs) {{
                var codes = container.querySelectorAll('pre code');
                for (var j = 0; j < codes.length; j++) {{
                    try {{ hljs.highlightElement(codes[j]); }} catch (e) {{}}
                }}
            }}
            // 3. 渲染 Mermaid 图（动态插入的节点不会被 startOnLoad 捕获，需手动 run）
            if (window.mermaid) {{
                var nodes = container.querySelectorAll('.mermaid');
                if (nodes.length) {{
                    try {{ mermaid.run({{ nodes: nodes }}); }} catch (e) {{}}
                }}
            }}
        }}

        function obShowLoading() {{
            var box = document.getElementById('onboardingContent');
            if (box) box.innerHTML = '<div class="onboarding-loading"><span class="onboarding-spinner"></span> AI 正在生成入门指南…</div>';
        }}

        function obShowError(msg) {{
            var box = document.getElementById('onboardingContent');
            if (box) box.innerHTML = '<div class="onboarding-error">⚠ ' + obEscapeHtml(msg) + '</div>';
        }}

        function loadOnboarding(audience) {{
            var box = document.getElementById('onboardingContent');
            if (!box) return;
            obSetTabActive(audience);
            // 命中缓存：直接渲染
            if (onboardingCache[audience]) {{
                obRenderMarkdown(onboardingCache[audience]);
                return;
            }}
            // 该受众正在请求：保持 loading，避免重复发请求
            if (onboardingPending[audience]) {{
                obShowLoading();
                return;
            }}
            obShowLoading();
            onboardingPending[audience] = true;
            var section = document.getElementById('onboardingSection');
            var dir = section.getAttribute('data-dir');
            var project = section.getAttribute('data-project');
            fetch('/api/onboarding', {{
                method: 'POST',
                headers: {{ 'Content-Type': 'application/json' }},
                body: JSON.stringify({{ dir: dir, project: project, audience: audience }}),
            }})
            .then(function(r) {{ return r.json(); }})
            .then(function(data) {{
                onboardingPending[audience] = false;
                if (data.error) {{
                    // 不缓存错误，允许重试；仅当仍是当前受众时显示
                    if (onboardingActive === audience) obShowError(data.error);
                    return;
                }}
                var guide = data.guide || '(生成内容为空)';
                onboardingCache[audience] = guide;
                // 仅当该受众仍是当前选中时才渲染，避免覆盖切换后的内容
                if (onboardingActive === audience) obRenderMarkdown(guide);
            }})
            .catch(function(err) {{
                onboardingPending[audience] = false;
                if (onboardingActive === audience) obShowError('请求失败: ' + err.message);
            }});
        }}

        // 绑定标签点击事件（懒加载：首次点击才请求）
        (function() {{
            var tabs = document.querySelectorAll('.onboarding-tab');
            for (var i = 0; i < tabs.length; i++) {{
                tabs[i].addEventListener('click', function() {{
                    loadOnboarding(this.getAttribute('data-audience'));
                }});
            }}
        }})();

        // ── 项目问答（DeepWiki 式交互）──
        function sendQuestion() {{
            const input = document.getElementById('qaInput');
            const btn = document.getElementById('qaSend');
            const question = input.value.trim();
            if (!question) return;
            const section = document.querySelector('.qa-section');
            const dir = section.getAttribute('data-dir');
            const project = section.getAttribute('data-project');
            const box = document.getElementById('qaMessages');

            // 清除空提示
            const empty = box.querySelector('.qa-empty');
            if (empty) empty.remove();

            // 用户气泡（右对齐蓝色）
            const userBubble = document.createElement('div');
            userBubble.className = 'qa-bubble user';
            userBubble.textContent = question;
            box.appendChild(userBubble);

            // loading 气泡（左对齐灰色）
            const loadingBubble = document.createElement('div');
            loadingBubble.className = 'qa-bubble ai loading';
            loadingBubble.innerHTML = '<span class="qa-typing"></span><span class="qa-typing"></span><span class="qa-typing"></span>';
            box.appendChild(loadingBubble);
            box.scrollTop = box.scrollHeight;

            input.value = '';
            input.disabled = true;
            btn.disabled = true;

            fetch('/api/ask', {{
                method: 'POST',
                headers: {{ 'Content-Type': 'application/json' }},
                body: JSON.stringify({{ question: question, dir: dir, project: project }}),
            }})
            .then(r => r.json())
            .then(data => {{
                loadingBubble.remove();
                const bubble = document.createElement('div');
                if (data.error) {{
                    bubble.className = 'qa-bubble error';
                    bubble.textContent = '⚠ ' + data.error;
                }} else {{
                    bubble.className = 'qa-bubble ai';
                    bubble.textContent = data.answer || '(无回答)';
                }}
                box.appendChild(bubble);
                box.scrollTop = box.scrollHeight;
            }})
            .catch(err => {{
                loadingBubble.remove();
                const bubble = document.createElement('div');
                bubble.className = 'qa-bubble error';
                bubble.textContent = '⚠ 请求失败: ' + err.message;
                box.appendChild(bubble);
                box.scrollTop = box.scrollHeight;
            }})
            .finally(() => {{
                input.disabled = false;
                btn.disabled = false;
                input.focus();
            }});
        }}

        // Enter 键发送
        (function() {{
            const inp = document.getElementById('qaInput');
            if (inp) {{
                inp.addEventListener('keydown', function(e) {{
                    if (e.key === 'Enter') {{ e.preventDefault(); sendQuestion(); }}
                }});
            }}
        }})();

        // ── 代码搜索（Greptile 式自然语言代码搜索）──
        var csEscapeHtml = function(s) {{
            return String(s).replace(/[&<>"']/g, function(c) {{
                return ({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}})[c];
            }});
        }};

        // 基于命中区间的关键词高亮（不依赖正则转义，按查询中的 | 拆分多关键词）
        var csHighlight = function(raw, query) {{
            raw = raw || '';
            var pieces = String(query || '').split('|');
            var i, p, lp, from, idx;
            var ranges = [];
            var lower = raw.toLowerCase();
            for (i = 0; i < pieces.length; i++) {{
                p = pieces[i].trim();
                if (!p) continue;
                lp = p.toLowerCase();
                from = 0;
                while (true) {{
                    idx = lower.indexOf(lp, from);
                    if (idx === -1) break;
                    ranges.push([idx, idx + lp.length]);
                    from = idx + lp.length;
                }}
            }}
            ranges.sort(function(a, b) {{ return a[0] - b[0]; }});
            var merged = [];
            var last = null;
            for (i = 0; i < ranges.length; i++) {{
                if (!last || ranges[i][0] > last[1]) {{
                    merged.push([ranges[i][0], ranges[i][1]]);
                    last = merged[merged.length - 1];
                }} else {{
                    if (ranges[i][1] > last[1]) last[1] = ranges[i][1];
                }}
            }}
            var out = '';
            var pos = 0;
            for (i = 0; i < merged.length; i++) {{
                out += csEscapeHtml(raw.slice(pos, merged[i][0]));
                out += '<mark>' + csEscapeHtml(raw.slice(merged[i][0], merged[i][1])) + '</mark>';
                pos = merged[i][1];
            }}
            out += csEscapeHtml(raw.slice(pos));
            return out;
        }};

        function runCodeSearch() {{
            var section = document.getElementById('codeSearchSection');
            if (!section) return;
            var repo = section.getAttribute('data-repo') || '';
            var language = section.getAttribute('data-language') || '';
            var input = document.getElementById('codeSearchInput');
            var btn = document.getElementById('codeSearchBtn');
            var query = (input.value || '').trim();
            if (!query) return;
            if (!repo || repo.indexOf('/') === -1) {{
                document.getElementById('codeSearchResults').innerHTML =
                    '<div class="search-error">ℹ️ 此为对比项目，不支持代码搜索（需单一 GitHub 仓库）</div>';
                return;
            }}

            var resultsBox = document.getElementById('codeSearchResults');
            var metaEl = document.getElementById('codeSearchMeta');
            btn.disabled = true;
            input.disabled = true;
            resultsBox.innerHTML = '<div class="search-loading">正在搜索代码…</div>';
            metaEl.innerHTML = '';

            fetch('/api/search-code', {{
                method: 'POST',
                headers: {{ 'Content-Type': 'application/json' }},
                body: JSON.stringify({{ repo: repo, project: repo, query: query, language: language }}),
            }})
            .then(function(r) {{ return r.json(); }})
            .then(function(data) {{ renderCodeSearchResults(data, query); }})
            .catch(function(err) {{
                resultsBox.innerHTML = '<div class="search-empty error">⚠ 请求失败: ' + csEscapeHtml(err.message) + '</div>';
            }})
            .finally(function() {{
                btn.disabled = false;
                input.disabled = false;
            }});
        }}

        function renderCodeSearchResults(data, query) {{
            var results = (data && data.results) || [];
            var resultsBox = document.getElementById('codeSearchResults');
            var metaEl = document.getElementById('codeSearchMeta');
            var inlineMeta = document.getElementById('codeSearchMetaInline');

            if (data && data.error) {{
                resultsBox.innerHTML = '<div class="search-empty error">⚠ ' + csEscapeHtml(data.error) + '</div>';
                metaEl.innerHTML = '';
                if (inlineMeta) inlineMeta.textContent = '';
                return;
            }}

            var total = (data && data.total != null) ? data.total : results.length;
            var source = (data && data.source) ? data.source : '';
            var srcLabel = source === 'local' ? '本地回退' : (source === 'github' ? 'GitHub' : source);
            var ms = (data && data.elapsed_ms != null) ? data.elapsed_ms : '';

            var metaHtml = '<span>找到 <b>' + total + '</b> 条结果</span>';
            if (srcLabel) metaHtml += '<span class="search-source">' + csEscapeHtml(srcLabel) + '</span>';
            if (ms !== '') metaHtml += '<span>耗时 ' + ms + 'ms</span>';
            metaEl.innerHTML = metaHtml;
            if (inlineMeta) inlineMeta.innerHTML = metaHtml;

            if (data && data.message) {{
                resultsBox.innerHTML = '<div class="search-empty">' + csEscapeHtml(data.message) + '</div>';
                return;
            }}
            if (!results.length) {{
                resultsBox.innerHTML = '<div class="search-empty">未找到匹配的代码，试试其他关键词或快捷标签</div>';
                return;
            }}

            resultsBox.innerHTML = '';
            for (var i = 0; i < results.length; i++) {{
                var r = results[i];
                var item = document.createElement('div');
                item.className = 'search-result';

                var head = document.createElement('div');
                head.className = 'search-head';
                var headHtml = '';
                if (r.type) headHtml += '<span class="match-type">' + csEscapeHtml(r.type) + '</span>';
                headHtml += '<span class="search-path">' + csEscapeHtml(r.path || r.name || '');
                if (r.line) headHtml += ' <span class="search-line">:' + csEscapeHtml(String(r.line)) + '</span>';
                headHtml += '</span>';
                if (r.score != null && r.score !== '') headHtml += '<span class="search-score">' + csEscapeHtml(String(r.score)) + '</span>';
                if (r.url) headHtml += '<a class="search-link" href="' + csEscapeHtml(r.url) + '" target="_blank" rel="noopener" onclick="event.stopPropagation()">↗</a>';
                head.innerHTML = headHtml;

                var code = document.createElement('pre');
                code.className = 'search-snippet';
                code.innerHTML = csHighlight(r.snippet || '', query);

                item.appendChild(head);
                item.appendChild(code);
                (function(itemEl, codeEl, rEl, q) {{
                    itemEl.addEventListener('click', function() {{
                        var expanded = itemEl.classList.toggle('expanded');
                        codeEl.innerHTML = csHighlight(expanded && rEl.context ? rEl.context : (rEl.snippet || ''), q);
                    }});
                }})(item, code, r, query);

                resultsBox.appendChild(item);
            }}
        }}

        // 代码搜索：Enter 键 + 快捷标签绑定
        (function() {{
            var inp = document.getElementById('codeSearchInput');
            if (inp) {{
                inp.addEventListener('keydown', function(e) {{
                    if (e.key === 'Enter') {{ e.preventDefault(); runCodeSearch(); }}
                }});
            }}
            var tags = document.querySelectorAll('#codeSearchSection .quick-tag');
            for (var i = 0; i < tags.length; i++) {{
                (function(tag) {{
                    tag.addEventListener('click', function() {{
                        var inp2 = document.getElementById('codeSearchInput');
                        inp2.value = tag.getAttribute('data-query');
                        runCodeSearch();
                    }});
                }})(tags[i]);
            }}
        }})();

        // ── 代码结构浏览器（CodeFlow / Greptile 式）──
        var FT_REPO = document.getElementById('filetreeSection').getAttribute('data-repo');
        var FT_LOADED = false;

        function formatSize(bytes) {{
            if (!bytes) return '';
            if (bytes < 1024) return bytes + ' B';
            if (bytes < 1048576) return (bytes / 1024).toFixed(1) + ' KB';
            return (bytes / 1048576).toFixed(2) + ' MB';
        }}

        function getLangFromPath(path) {{
            var ext = (path.split('.').pop() || '').toLowerCase();
            var map = {{
                py: 'python', js: 'javascript', ts: 'typescript', jsx: 'javascript', tsx: 'typescript',
                java: 'java', c: 'c', h: 'c', cpp: 'cpp', cc: 'cpp', cxx: 'cpp', go: 'go', rs: 'rust',
                rb: 'ruby', php: 'php', sh: 'bash', bash: 'bash', zsh: 'bash', yml: 'yaml', yaml: 'yaml',
                json: 'json', xml: 'xml', html: 'xml', htm: 'xml', css: 'css', scss: 'scss', md: 'markdown',
                markdown: 'markdown', sql: 'sql', vue: 'xml', toml: 'ini', ini: 'ini', cfg: 'ini',
                conf: 'ini', txt: 'plaintext', gradle: 'gradle', kt: 'kotlin', swift: 'swift'
            }};
            var base = (path.split('/').pop() || '').toLowerCase();
            if (base === 'dockerfile') return 'dockerfile';
            if (base === 'makefile' || base === 'gnumakefile') return 'makefile';
            return map[ext] || 'plaintext';
        }}

        // 将扁平的路径列表构建为嵌套目录树
        function buildTree(flatList) {{
            var root = {{ name: '', path: '', children: {{}}, isDir: true, type: 'tree' }};
            flatList.forEach(function(entry) {{
                var parts = entry.path.split('/');
                var node = root;
                parts.forEach(function(part, i) {{
                    var isLast = i === parts.length - 1;
                    if (!node.children[part]) {{
                        node.children[part] = {{
                            name: part,
                            path: parts.slice(0, i + 1).join('/'),
                            isDir: isLast ? (entry.type === 'tree') : true,
                            children: {{}},
                            size: (isLast && entry.type === 'blob') ? (entry.size || 0) : 0,
                            type: isLast ? entry.type : 'tree'
                        }};
                    }}
                    node = node.children[part];
                }});
            }});
            return root;
        }}

        // 目录优先、名字次序排序
        function sortTree(node) {{
            var arr = Object.keys(node.children).map(function(k) {{ return node.children[k]; }});
            arr.sort(function(a, b) {{
                if (a.isDir !== b.isDir) return a.isDir ? -1 : 1;
                return a.name.localeCompare(b.name);
            }});
            node._sorted = arr;
            arr.forEach(function(c) {{ sortTree(c); }});
        }}

        function renderTree(node) {{
            var ul = document.createElement('ul');
            ul.className = 'tree-list';
            (node._sorted || []).forEach(function(child) {{
                ul.appendChild(renderNode(child));
            }});
            return ul;
        }}

        function renderNode(node) {{
            var li = document.createElement('li');
            li.className = 'tree-node';
            if (node.isDir) {{
                var row = document.createElement('div');
                row.className = 'tree-row tree-folder';
                var toggle = document.createElement('span');
                toggle.className = 'tree-toggle';
                toggle.textContent = '▶';
                var icon = document.createElement('span');
                icon.className = 'tree-icon';
                icon.textContent = '📁';
                var name = document.createElement('span');
                name.className = 'tree-name';
                name.textContent = node.name;
                row.appendChild(toggle); row.appendChild(icon); row.appendChild(name);
                li.appendChild(row);
                var childWrap = document.createElement('div');
                childWrap.className = 'tree-children';
                childWrap.style.display = 'none';
                (node._sorted || []).forEach(function(c) {{ childWrap.appendChild(renderNode(c)); }});
                row.addEventListener('click', function(e) {{
                    e.stopPropagation();
                    var expanded = childWrap.style.display !== 'none';
                    childWrap.style.display = expanded ? 'none' : 'block';
                    toggle.textContent = expanded ? '▶' : '▼';
                }});
                li.appendChild(childWrap);
            }} else {{
                var row = document.createElement('div');
                row.className = 'tree-row tree-file';
                var toggle = document.createElement('span');
                toggle.className = 'tree-toggle';
                var icon = document.createElement('span');
                icon.className = 'tree-icon';
                icon.textContent = '📄';
                var name = document.createElement('span');
                name.className = 'tree-name';
                name.textContent = node.name;
                row.appendChild(toggle); row.appendChild(icon); row.appendChild(name);
                var sz = formatSize(node.size);
                if (sz) {{
                    var szEl = document.createElement('span');
                    szEl.className = 'tree-size';
                    szEl.textContent = sz;
                    row.appendChild(szEl);
                }}
                row.addEventListener('click', function(e) {{
                    e.stopPropagation();
                    loadFile(node.path, row);
                }});
                li.appendChild(row);
            }}
            return li;
        }}

        function loadFileTree() {{
            if (FT_LOADED) return;
            FT_LOADED = true;
            var container = document.getElementById('filetreeContainer');
            if (!FT_REPO || FT_REPO.indexOf('/') === -1) {{
                container.innerHTML = '<div class="tree-error">ℹ️ 此为对比项目，不支持代码结构浏览（需单一 GitHub 仓库）</div>';
                return;
            }}
            container.innerHTML = '<div class="tree-loading">⏳ 正在加载文件结构...</div>';
            fetch('/api/filetree?repo=' + encodeURIComponent(FT_REPO))
                .then(function(r) {{ return r.json(); }})
                .then(function(data) {{
                    if (data.error) {{
                        container.innerHTML = '<div class="tree-error">⚠ ' + data.error + '</div>';
                        return;
                    }}
                    var entries = (data.tree || []).filter(function(e) {{
                        return e.type === 'tree' || e.type === 'blob';
                    }});
                    var limited = entries.slice(0, 200);  // 限制前 200 项
                    var tree = buildTree(limited);
                    sortTree(tree);
                    container.innerHTML = '';
                    container.appendChild(renderTree(tree));
                    if (data.truncated || entries.length > 200) {{
                        var note = document.createElement('div');
                        note.className = 'tree-note';
                        note.textContent = '⚠ 仓库文件较多，仅显示前 200 项' +
                            (data.truncated ? '（GitHub 返回已被截断）' : '');
                        container.appendChild(note);
                    }}
                }})
                .catch(function(err) {{
                    container.innerHTML = '<div class="tree-error">⚠ 加载失败: ' + err.message + '</div>';
                }});
        }}

        function loadFile(path, rowEl) {{
            var viewer = document.getElementById('fileViewer');
            var prev = document.querySelectorAll('.tree-row.active');
            for (var i = 0; i < prev.length; i++) prev[i].classList.remove('active');
            if (rowEl) rowEl.classList.add('active');
            viewer.style.display = 'block';
            viewer.innerHTML = '<div class="tree-loading">⏳ 正在加载文件内容...</div>';
            fetch('/api/file?repo=' + encodeURIComponent(FT_REPO) + '&path=' + encodeURIComponent(path))
                .then(function(r) {{ return r.json(); }})
                .then(function(data) {{
                    if (data.error) {{
                        viewer.innerHTML = '<div class="tree-error">⚠ ' + data.error + '</div>';
                        return;
                    }}
                    var lang = getLangFromPath(path);
                    var sizeStr = formatSize(data.size);
                    var header = document.createElement('div');
                    header.className = 'file-header';
                    var pth = document.createElement('span');
                    pth.className = 'file-path';
                    pth.textContent = path;
                    var sz = document.createElement('span');
                    sz.className = 'file-size';
                    sz.textContent = sizeStr;
                    header.appendChild(pth); header.appendChild(sz);
                    var pre = document.createElement('pre');
                    pre.className = 'file-content';
                    var code = document.createElement('code');
                    code.className = 'language-' + lang;
                    code.textContent = data.content;
                    pre.appendChild(code);
                    viewer.innerHTML = '';
                    viewer.appendChild(header);
                    viewer.appendChild(pre);
                    if (window.hljs) {{
                        try {{ hljs.highlightElement(code); }} catch (e) {{}}
                    }}
                }})
                .catch(function(err) {{
                    viewer.innerHTML = '<div class="tree-error">⚠ 加载失败: ' + err.message + '</div>';
                }});
        }}

        // ── 社区洞察（借鉴 Zread.ai 社区讨论摘要）──
        var ciEscapeHtml = function(s) {{
            return String(s == null ? '' : s).replace(/[&<>"']/g, function(c) {{
                return ({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}})[c];
            }});
        }};

        function ciFormatNum(n) {{
            n = Number(n || 0);
            if (n >= 1000) return (n / 1000).toFixed(1) + 'k';
            return String(n);
        }}

        function ciFormatDate(iso) {{
            if (!iso) return '—';
            var d = new Date(iso);
            if (isNaN(d.getTime())) return iso;
            var y = d.getFullYear();
            var m = String(d.getMonth() + 1).padStart(2, '0');
            var day = String(d.getDate()).padStart(2, '0');
            return y + '-' + m + '-' + day;
        }}

        function loadCommunity() {{
            var section = document.getElementById('communitySection');
            if (!section) return;
            var repo = section.getAttribute('data-repo') || '';
            var body = document.getElementById('communityBody');
            if (!repo || repo.indexOf('/') === -1) {{
                body.innerHTML = '<div class="community-error">ℹ️ 此为对比项目，不支持社区洞察（需单一 GitHub 仓库）</div>';
                return;
            }}
            body.innerHTML = '<div class="community-loading">⏳ 正在加载社区洞察…</div>';

            fetch('/api/community?repo=' + encodeURIComponent(repo))
                .then(function(r) {{ return r.json(); }})
                .then(function(data) {{ renderCommunity(data, repo); }})
                .catch(function(err) {{
                    body.innerHTML = '<div class="community-error">⚠ 加载失败: ' + ciEscapeHtml(err.message) + '</div>';
                }});
        }}

        function renderCommunity(data, repo) {{
            var body = document.getElementById('communityBody');
            var metaInline = document.getElementById('communityMetaInline');
            if (!data || data.error) {{
                body.innerHTML = '<div class="community-error">⚠ ' + ciEscapeHtml((data && data.error) ? data.error : '加载失败') + '</div>';
                return;
            }}

            var info = data.repo_info || {{}};
            var issues = data.hot_issues || [];
            var prs = data.active_prs || [];
            var contributors = data.contributors || [];
            var releases = data.releases || [];

            var html = '';

            // 1. 基本信息卡片行
            html += '<div class="ci-stats-row">';
            html += ciStatCard('⭐', ciFormatNum(info.stars), 'Stars');
            html += ciStatCard('🍴', ciFormatNum(info.forks), 'Forks');
            html += ciStatCard('❗', ciFormatNum(info.open_issues), 'Open Issues');
            html += ciStatCard('📅', ciFormatDate(info.pushed_at), '最近更新');
            html += '</div>';

            // 主题标签（topics）
            html += '<div class="ci-subhead">主题标签</div>';
            var topics = info.topics || [];
            if (topics.length) {{
                html += '<div class="ci-topics">';
                for (var i = 0; i < topics.length; i++) {{
                    html += '<span class="ci-topic">' + ciEscapeHtml(topics[i]) + '</span>';
                }}
                html += '</div>';
            }} else {{
                html += '<div class="ci-no-topics">暂无主题标签</div>';
            }}

            // 2. 热门 Issues
            html += '<div class="ci-subhead">🔥 热门 Issues</div>';
            html += ciRenderIssues(issues, repo);

            // 3. 活跃 PRs
            html += '<div class="ci-subhead">🔀 活跃 PRs</div>';
            html += ciRenderPRs(prs, repo);

            // 4. 核心贡献者
            html += '<div class="ci-subhead">👥 核心贡献者</div>';
            html += ciRenderContributors(contributors);

            // 5. 最新版本
            html += '<div class="ci-subhead">🏷️ 最新版本</div>';
            html += ciRenderReleases(releases, repo);

            body.innerHTML = html;

            var counts = [];
            if (issues.length) counts.push(issues.length + ' Issues');
            if (prs.length) counts.push(prs.length + ' PRs');
            if (contributors.length) counts.push(contributors.length + ' 贡献者');
            if (releases.length) counts.push(releases.length + ' 版本');
            if (metaInline) metaInline.textContent = counts.join(' · ');
        }}

        function ciStatCard(icon, value, label) {{
            return '<div class="ci-stat-card">' +
                '<span class="ci-stat-icon">' + icon + '</span>' +
                '<span class="ci-stat-body">' +
                '<span class="ci-stat-value">' + ciEscapeHtml(value) + '</span>' +
                '<span class="ci-stat-label">' + ciEscapeHtml(label) + '</span>' +
                '</span></div>';
        }}

        function ciRenderIssues(issues, repo) {{
            if (!issues.length) return '<div class="ci-empty">暂无热门 Issues</div>';
            var html = '<div class="ci-list">';
            for (var i = 0; i < issues.length; i++) {{
                var it = issues[i];
                var url = it.url || ('https://github.com/' + repo + '/issues/' + it.number);
                html += '<a class="ci-item" href="' + ciEscapeHtml(url) + '" target="_blank" rel="noopener">';
                html += '<div class="ci-item-head">';
                html += '<span class="ci-item-num">#' + ciEscapeHtml(it.number) + '</span>';
                html += '<span class="ci-item-title">' + ciEscapeHtml(it.title) + '</span>';
                html += '<span class="ci-comments">💬 ' + ciEscapeHtml(it.comments || 0) + '</span>';
                html += '</div>';
                var labels = it.labels || [];
                if (labels.length) {{
                    html += '<div class="ci-labels">';
                    for (var j = 0; j < labels.length; j++) {{
                        html += '<span class="ci-label">' + ciEscapeHtml(labels[j]) + '</span>';
                    }}
                    html += '</div>';
                }}
                html += '</a>';
            }}
            html += '</div>';
            return html;
        }}

        function ciRenderPRs(prs, repo) {{
            if (!prs.length) return '<div class="ci-empty">暂无活跃 PRs</div>';
            var html = '<div class="ci-list">';
            for (var i = 0; i < prs.length; i++) {{
                var pr = prs[i];
                var url = pr.url || ('https://github.com/' + repo + '/pull/' + pr.number);
                html += '<a class="ci-item" href="' + ciEscapeHtml(url) + '" target="_blank" rel="noopener">';
                html += '<div class="ci-item-head">';
                html += '<span class="ci-item-num">#' + ciEscapeHtml(pr.number) + '</span>';
                html += '<span class="ci-item-title">' + ciEscapeHtml(pr.title) + '</span>';
                html += '</div>';
                html += '<div class="ci-meta">由 <b>' + ciEscapeHtml(pr.user || '') + '</b> 提交</div>';
                html += '</a>';
            }}
            html += '</div>';
            return html;
        }}

        function ciRenderContributors(contributors) {{
            if (!contributors.length) return '<div class="ci-empty">暂无贡献者数据</div>';
            var html = '<div class="ci-contributors">';
            for (var i = 0; i < contributors.length; i++) {{
                var c = contributors[i];
                var profileUrl = 'https://github.com/' + encodeURIComponent(c.login);
                html += '<a class="ci-contributor" href="' + ciEscapeHtml(profileUrl) + '" target="_blank" rel="noopener">';
                if (c.avatar_url) {{
                    html += '<img src="' + ciEscapeHtml(c.avatar_url) + '" alt="' + ciEscapeHtml(c.login || '') + '" loading="lazy">';
                }}
                html += '<span class="ci-login">' + ciEscapeHtml(c.login || '') + '</span>';
                html += '<span class="ci-contribs">' + ciFormatNum(c.contributions) + ' 次贡献</span>';
                html += '</a>';
            }}
            html += '</div>';
            return html;
        }}

        function ciRenderReleases(releases, repo) {{
            if (!releases.length) return '<div class="ci-empty">暂无版本发布</div>';
            var html = '<div class="ci-list">';
            for (var i = 0; i < releases.length; i++) {{
                var r = releases[i];
                var url = r.url || ('https://github.com/' + repo + '/releases');
                html += '<a class="ci-item" href="' + ciEscapeHtml(url) + '" target="_blank" rel="noopener">';
                html += '<div class="ci-item-head">';
                html += '<span class="ci-item-num">' + ciEscapeHtml(r.tag || '') + '</span>';
                html += '<span class="ci-item-title">' + ciEscapeHtml(r.name || r.tag || '') + '</span>';
                html += '</div>';
                html += '<div class="ci-meta">发布于 ' + ciFormatDate(r.published_at) + '</div>';
                html += '</a>';
            }}
            html += '</div>';
            return html;
        }}

        // 页面加载后获取目录树（懒加载：文件内容点击时才请求）
        loadFileTree();
        // 页面加载后加载社区洞察
        loadCommunity();
    </script>
</body>
</html>
"""

