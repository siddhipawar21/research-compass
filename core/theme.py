from __future__ import annotations

import html as _html
import json as _json

import streamlit as st
import streamlit.components.v1 as components

from core.citations import UNAVAILABLE, safe_url

LIGHT = {
    "bg1": "#F7F5EF",
    "bg2": "#EFEBDF",
    "surface": "#FFFFFF",
    "ink": "#14182B",
    "muted": "#5B6478",
    "line": "rgba(20,24,43,.10)",
    "brass": "#B9822E",
    "sage": "#2F8F5B",
    "coral": "#C4443A",
    "glass": "rgba(255,255,255,.86)",
    "shadow": "0 10px 28px -18px rgba(20,24,43,.28)",
    "ring_inner": "#FFFFFF",
    "app_grad": "radial-gradient(900px 420px at 8% -10%, rgba(185,130,46,.10), transparent 58%), radial-gradient(800px 480px at 100% 0%, rgba(47,143,91,.07), transparent 55%), linear-gradient(180deg,#F7F5EF 0%,#EFEBDF 100%)",
    "sidebar": "linear-gradient(180deg,#FFFFFF,#F7F5EF)",
    "input_bg": "#FFFFFF",
    "card_bg": "#FFFFFF",
}

DARK = {
    "bg1": "#0A1029",
    "bg2": "#18234A",
    "surface": "#111A3D",
    "ink": "#E8ECF8",
    "muted": "#AAB4D0",
    "line": "rgba(255,255,255,.12)",
    "brass": "#E0B463",
    "sage": "#6FCF97",
    "coral": "#FF7A7A",
    "glass": "rgba(255,255,255,.05)",
    "shadow": "0 16px 32px -20px rgba(0,0,0,.55)",
    "ring_inner": "#111A3D",
    "app_grad": "radial-gradient(900px 420px at 8% -10%, rgba(224,180,99,.12), transparent 58%), radial-gradient(800px 480px at 100% 0%, rgba(90,110,255,.10), transparent 55%), linear-gradient(180deg,#0A1029 0%,#111A3D 100%)",
    "sidebar": "linear-gradient(180deg,#111A3D,#0A1029)",
    "input_bg": "#18234A",
    "card_bg": "#111A3D",
}


def _css(t: dict[str, str]) -> str:
    return f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Source+Serif+4:opsz,wght@8..60,600;8..60,700&family=IBM+Plex+Sans:wght@400;500;600&display=swap');
:root, .stApp {{
  --bg:{t['bg1']}; --bg1:{t['bg1']}; --bg2:{t['bg2']}; --surface:{t['surface']}; --surface-2:{t['bg2']};
  --text:{t['ink']}; --ink:{t['ink']}; --text-muted:{t['muted']}; --muted:{t['muted']};
  --border:{t['line']}; --line:{t['line']}; --accent:{t['brass']}; --brass:{t['brass']};
  --success:{t['sage']}; --sage:{t['sage']}; --danger:{t['coral']}; --coral:{t['coral']};
  --glass:{t['glass']}; --shadow:{t['shadow']}; --ring-inner:{t['ring_inner']};
  --display:'Source Serif 4','Georgia',serif;
  --body:'IBM Plex Sans','Segoe UI',system-ui,sans-serif;
}}
.stApp{{
  background:{t['app_grad']};
  color:var(--ink); font-family:var(--body);
}}
header[data-testid="stHeader"]{{background:transparent;}}
.block-container{{max-width:1180px;padding-top:1.4rem;padding-bottom:4rem;}}
h1,h2,h3,h4{{font-family:var(--display);letter-spacing:-.02em;color:var(--ink);}}
p,li,label,.stMarkdown{{font-family:var(--body); color:var(--ink);}}
[data-testid="stMarkdownContainer"],
[data-testid="stMarkdownContainer"] p,
[data-testid="stCaptionContainer"],
[data-testid="stCaptionContainer"] p,
[data-testid="stWidgetLabel"],
[data-testid="stWidgetLabel"] p,
[data-testid="stChatMessage"],
[data-testid="stChatMessage"] p,
[data-testid="stAlert"],
[data-testid="stExpander"] p,
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"],
[data-testid="stSidebar"] label,
.stChatMessage {{
  color:var(--ink)!important;
}}
textarea::placeholder, .stTextInput input::placeholder {{
  color:var(--muted)!important; opacity:.85;
}}
a{{color:var(--brass);text-decoration:none;border-bottom:1px solid color-mix(in srgb, var(--brass) 40%, transparent);}}
a:hover{{border-bottom-color:var(--brass);}}
[data-testid="stSidebar"]{{
  background:{t['sidebar']}; border-right:1px solid var(--line);
}}
.stTextArea textarea, .stTextInput input,
[data-testid="stTextArea"] textarea, [data-testid="stTextInputField"]{{
  background:{t['input_bg']}!important; color:var(--ink)!important;
  border:1px solid var(--line)!important; border-radius:12px!important;
  box-shadow:var(--shadow); font-family:var(--body)!important; line-height:1.55;
}}
.stTextArea textarea:focus, .stTextInput input:focus,
[data-testid="stTextArea"] textarea:focus, [data-testid="stTextInputField"]:focus{{
  border-color:var(--brass)!important;
  box-shadow:0 0 0 3px color-mix(in srgb, var(--brass) 22%, transparent)!important;
}}
.stButton>button, .stDownloadButton>button,
[data-testid^="stBaseButton"], [data-testid="stDownloadButton"] button{{
  font-family:var(--body); font-weight:600; letter-spacing:.01em;
  border-radius:10px; padding:.55rem 1.15rem; color:#fff;
  background:var(--brass); border:1px solid var(--brass);
  box-shadow:0 8px 18px -10px color-mix(in srgb, var(--brass) 70%, transparent);
}}
.stButton>button:hover, .stDownloadButton>button:hover,
[data-testid^="stBaseButton"]:hover, [data-testid="stDownloadButton"] button:hover{{
  filter:brightness(1.05); color:#fff; border-color:var(--brass);
}}
.stButton>button:focus-visible, [data-testid^="stBaseButton"]:focus-visible{{
  outline:3px solid color-mix(in srgb, var(--brass) 50%, transparent); outline-offset:3px;
}}
.stTabs [data-baseweb="tab-list"], [data-testid="stTabs"]{{gap:4px; border-bottom:1px solid var(--line);}}
.stTabs [data-baseweb="tab"], [data-testid="stTab"]{{
  height:auto; padding:.5rem .9rem; border-radius:10px 10px 0 0;
  background:transparent; color:var(--muted); font-family:var(--body); font-weight:500;
}}
.stTabs [aria-selected="true"], [data-testid="stTab"][aria-selected="true"]{{
  color:var(--ink)!important; background:var(--surface); box-shadow:inset 0 -2px 0 var(--brass);
}}
[data-testid="stExpander"]{{background:var(--surface); border:1px solid var(--line)!important; border-radius:12px;}}
[data-testid="stDataFrame"]{{border:1px solid var(--line); border-radius:12px; overflow:hidden;}}
.rc-hero-title{{font-family:var(--display); font-weight:700; font-size:clamp(2.1rem,4.4vw,3.2rem); line-height:1.08; margin:.15rem 0 .55rem; color:var(--ink);}}
.rc-hero-sub{{color:var(--muted); font-size:1.06rem; line-height:1.6; max-width:36rem; margin:0 0 1rem;}}
.rc-mark{{display:inline-flex;align-items:center;gap:.55rem;font-weight:600;color:var(--brass);font-size:.88rem;letter-spacing:.04em;text-transform:uppercase;}}
.rc-cards{{display:grid; grid-template-columns:repeat(auto-fit,minmax(220px,1fr)); gap:16px; margin:1rem 0 1.4rem;}}
.rc-card{{
  position:relative; padding:1.15rem 1.2rem; border-radius:16px;
  background:{t['card_bg']}; border:1px solid var(--line); box-shadow:var(--shadow);
}}
.rc-card .k{{color:var(--muted); font-size:.86rem; margin-bottom:.3rem;}}
.rc-card .v{{font-family:var(--display); font-weight:700; font-size:1.85rem; line-height:1.15; color:var(--ink);}}
.rc-card .n{{color:var(--muted); font-size:.9rem; margin-top:.45rem; line-height:1.5;}}
.rc-card.good .v{{color:var(--sage);}} .rc-card.bad .v{{color:var(--coral);}} .rc-card.brass .v{{color:var(--brass);}}
.rc-ring{{
  --p:50; width:148px; height:148px; border-radius:50%; display:grid; place-items:center; position:relative;
  background:conic-gradient(var(--brass) calc(var(--p)*1%), color-mix(in srgb, var(--muted) 25%, transparent) 0);
  box-shadow:var(--shadow);
}}
.rc-ring::before{{
  content:""; position:absolute; inset:12px; border-radius:50%;
  background:var(--ring-inner);
}}
.rc-ring span{{position:relative; font-family:var(--display); font-weight:700; font-size:2.2rem; color:var(--ink);}}
.rc-ring-label{{text-align:center; color:var(--muted); font-size:.9rem; margin-top:.55rem;}}
.rc-chat{{display:flex; flex-direction:column; gap:12px; margin:.5rem 0;}}
.rc-msg{{max-width:82%; padding:.85rem 1.05rem; border-radius:14px; border:1px solid var(--line); background:var(--surface); box-shadow:var(--shadow); line-height:1.6; color:var(--ink);}}
.rc-msg .who{{font-family:var(--display); font-weight:700; margin-bottom:.25rem;}}
.rc-msg.advocate{{align-self:flex-start; border-left:3px solid var(--sage);}} .rc-msg.advocate .who{{color:var(--sage);}}
.rc-msg.skeptic{{align-self:flex-end; border-right:3px solid var(--coral);}} .rc-msg.skeptic .who{{color:var(--coral);}}
.rc-msg.judge{{align-self:center; max-width:92%; background:color-mix(in srgb, var(--brass) 8%, var(--surface));}}
.rc-msg.judge .who{{color:var(--brass);}}
.rc-src{{display:inline-block; margin:2px 4px 2px 0; padding:.12rem .5rem; border-radius:999px; border:1px solid var(--line); background:var(--surface); font-size:.8rem; color:var(--ink);}}
a.rc-src{{color:var(--brass);}}
.rc-src:hover{{border-color:var(--brass);}}
.rc-pill{{display:inline-block;padding:.12rem .55rem;border-radius:999px;font-size:.78rem;font-weight:600;margin-right:6px;}}
.rc-pill.sage{{background:color-mix(in srgb, var(--sage) 14%, transparent);color:var(--sage);border:1px solid color-mix(in srgb, var(--sage) 35%, transparent);}}
.rc-pill.coral{{background:color-mix(in srgb, var(--coral) 12%, transparent);color:var(--coral);border:1px solid color-mix(in srgb, var(--coral) 35%, transparent);}}
.rc-pill.brass{{background:color-mix(in srgb, var(--brass) 14%, transparent);color:var(--brass);border:1px solid color-mix(in srgb, var(--brass) 35%, transparent);}}
.rc-pill.muted{{background:transparent;color:var(--muted);border:1px solid var(--line);}}
.rc-tag{{display:inline-block;font-size:.75rem;color:var(--muted);margin-right:6px;border:1px solid var(--line);border-radius:999px;padding:.08rem .5rem;background:var(--surface);}}
.rc-ev-col{{padding:1rem 1.05rem;border-radius:14px;border:1px solid var(--line);min-height:8rem;background:var(--surface);}}
.rc-ev-col.sage{{background:color-mix(in srgb, var(--sage) 8%, var(--surface));}}
.rc-ev-col.coral{{background:color-mix(in srgb, var(--coral) 7%, var(--surface));}}
.rc-ev-col h3{{margin-top:0;font-family:var(--display);color:var(--ink);}}
.rc-ev-item{{margin:0 0 .9rem;line-height:1.5;color:var(--ink);}}
.rc-venue-card,.rc-repro-item,.rc-source-card{{
  padding:.95rem 1.05rem;margin:0 0 .75rem;border-radius:12px;border:1px solid var(--line);
  background:var(--surface); box-shadow:var(--shadow);
}}
.rc-deadline-missing,.rc-unavail{{color:var(--muted); font-size:.85rem;}}
.rc-rating-wrap{{margin:0 0 1rem;}}
.rc-rating-wrap .rc-pill{{font-size:1rem;padding:.32rem .85rem;}}
.rc-count{{color:var(--muted); font-size:.86rem; text-align:right;}}
@media (max-width:900px){{
  .rc-cards{{grid-template-columns:1fr;}}
  .rc-msg{{max-width:96%;}}
  .block-container{{padding-left:1rem;padding-right:1rem;}}
}}
@media (prefers-reduced-motion:reduce){{
  .stButton>button,.stDownloadButton>button,[data-testid^="stBaseButton"]{{transition:none;}}
}}
</style>
"""


_SPHERE = """
<div style="width:100%;height:100%;position:relative">
<script type="application/json" id="rc-sphere-cfg">__RC_SPHERE_CFG__</script>
<canvas id="c" style="width:100%;height:100%;display:block;cursor:grab" aria-label="Research connections globe"></canvas>
</div>
<script>
(function(){
  var cv=document.getElementById('c'), cx=cv.getContext('2d');
  var cfg={n:110,cited:12,novelty:50,theme:'light'};
  try{cfg=Object.assign(cfg, JSON.parse(document.getElementById('rc-sphere-cfg').textContent));}catch(e){}
  var dark=cfg.theme==='dark';
  var reduce=window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var W,H,DPR=Math.min(window.devicePixelRatio||1,2);
  function size(){var r=cv.getBoundingClientRect();W=r.width;H=r.height;cv.width=W*DPR;cv.height=H*DPR;cx.setTransform(DPR,0,0,DPR,0,0);}
  size(); window.addEventListener('resize',size);
  var N=Math.max(12, Math.min(160, parseInt(cfg.n,10)||110));
  var citedN=Math.max(0, Math.min(N, parseInt(cfg.cited,10)||0));
  var novelty=Math.max(0, Math.min(100, parseFloat(cfg.novelty)||50))/100;
  var pts=[], golden=Math.PI*(3-Math.sqrt(5));
  for(var i=0;i<N;i++){
    var y=1-(i/(N-1))*2, r=Math.sqrt(1-y*y), t=golden*i;
    var glow=(citedN>0) && (Math.floor(i*citedN/N)!==Math.floor((i-1)*citedN/N) || i===0);
    pts.push({x:Math.cos(t)*r,y:y,z:Math.sin(t)*r,cited:glow});
  }
  var edges=[];
  var thresh=N>80?0.30:0.42;
  for(var a=0;a<N;a++)for(var b=a+1;b<N;b++){
    var dx=pts[a].x-pts[b].x,dy=pts[a].y-pts[b].y,dz=pts[a].z-pts[b].z;
    if(dx*dx+dy*dy+dz*dz<thresh)edges.push([a,b]);
  }
  var ring=[]; for(var k=0;k<96;k++){var th=k/96*Math.PI*2;ring.push({x:Math.cos(th)*1.32,y:0,z:Math.sin(th)*1.32,major:(k%8===0)});}
  var ry=0.4, rx=-0.35, vy=0.004, drag=false, lx=0, ly=0;
  cv.addEventListener('pointerdown',function(e){drag=true;lx=e.clientX;ly=e.clientY;cv.style.cursor='grabbing';});
  window.addEventListener('pointerup',function(){drag=false;cv.style.cursor='grab';});
  window.addEventListener('pointermove',function(e){
    if(!drag)return; ry+=(e.clientX-lx)*0.008; rx+=(e.clientY-ly)*0.008;
    rx=Math.max(-1.2,Math.min(1.2,rx)); lx=e.clientX; ly=e.clientY;
  });
  function proj(p){
    var cy=Math.cos(ry),sy=Math.sin(ry),cxr=Math.cos(rx),sxr=Math.sin(rx);
    var x=p.x*cy+p.z*sy, z=-p.x*sy+p.z*cy, y=p.y*cxr-z*sxr; z=p.y*sxr+z*cxr;
    var s=Math.min(W,H)*0.30, f=3.2/(3.2+z*0.9);
    return {x:W/2+x*s*f, y:H/2+y*s*f, z:z, f:f};
  }
  function frame(){
    cx.clearRect(0,0,W,H);
    if(!reduce&&!drag)ry+=vy;
    var P=pts.map(proj);
    cx.lineWidth=1;
    edges.forEach(function(e){
      var A=P[e[0]],B=P[e[1]],d=(A.z+B.z)/2, al=0.06+0.18*(1-(d+1)/2);
      cx.strokeStyle=(dark?'rgba(152,170,255,':'rgba(90,100,140,')+al.toFixed(3)+')';
      cx.beginPath(); cx.moveTo(A.x,A.y); cx.lineTo(B.x,B.y); cx.stroke();
    });
    var R=ring.map(proj);
    var ringAl=0.35+0.65*novelty;
    function drawRing(front){
      R.forEach(function(q,i){ if((q.z>=0)!==front)return;
        var al=front?ringAl:ringAl*0.4, sz=(ring[i].major?2.6:1.4)*q.f;
        cx.fillStyle='rgba(185,130,46,'+al+')'; cx.beginPath(); cx.arc(q.x,q.y,sz,0,6.283); cx.fill();
      });
    }
    drawRing(false);
    P.map(function(q,i){return {q:q,i:i};}).sort(function(a,b){return a.q.z-b.q.z;}).forEach(function(o){
      var q=o.q, c=pts[o.i].cited, depth=(q.z+1)/2, al=0.4+0.6*(1-depth);
      var sz=(c?4.2:2.2)*q.f;
      if(c){cx.shadowColor='rgba(185,130,46,'+(0.4+0.4*novelty)+')';cx.shadowBlur=8+14*novelty;cx.fillStyle='rgba(185,130,46,'+al+')';}
      else{cx.shadowBlur=0;cx.fillStyle=dark?'rgba(200,212,255,'+al+')':'rgba(70,82,120,'+al+')';}
      cx.beginPath(); cx.arc(q.x,q.y,sz,0,6.283); cx.fill(); cx.shadowBlur=0;
    });
    drawRing(true);
    if(!reduce)requestAnimationFrame(frame);
  }
  frame();
})();
</script>
"""


def current_theme() -> str:
    return "dark" if st.session_state.get("rc_theme") == "dark" else "light"


def inject_theme(theme: str | None = None) -> None:
    theme = theme or current_theme()
    tokens = DARK if theme == "dark" else LIGHT
    st.markdown(_css(tokens), unsafe_allow_html=True)


def theme_colors(theme: str | None = None) -> dict[str, str]:
    theme = theme or current_theme()
    return DARK if theme == "dark" else LIGHT


def plotly_layout(theme: str | None = None) -> dict:
    c = theme_colors(theme)
    return dict(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font_color=c["ink"],
        xaxis=dict(showgrid=False, zeroline=False, color=c["muted"]),
        yaxis=dict(showgrid=False, color=c["muted"]),
        legend=dict(font=dict(color=c["ink"])),
        margin=dict(l=10, r=10, t=36, b=10),
    )


def _sphere_iframe(n: int = 110, cited: int = 12, novelty: float = 50, theme: str | None = None) -> None:
    theme = theme or current_theme()
    cfg = _json.dumps({"n": int(n), "cited": int(cited), "novelty": float(novelty), "theme": theme})
    components.html(_SPHERE.replace("__RC_SPHERE_CFG__", cfg), height=320)


def hero() -> None:
    left, right = st.columns([1.2, 1], vertical_alignment="center")
    with left:
        st.markdown(
            '<div class="rc-mark">Research Compass</div>'
            '<div class="rc-hero-title">Research Compass</div>'
            '<p class="rc-hero-sub">Turn a research abstract into a grounded research intelligence report.</p>',
            unsafe_allow_html=True,
        )
    with right:
        _sphere_iframe()


def report_sphere(novelty_score: float, source_count: int, cited_count: int) -> None:
    _sphere_iframe(
        n=min(max(int(source_count), 12), 160),
        cited=max(0, int(cited_count)),
        novelty=float(novelty_score),
    )


def stance_pill(stance: str) -> str:
    m = {"supporting": ("sage", "Supports"), "contradicting": ("coral", "Contradicts"),
         "neutral": ("brass", "Neutral")}
    tone, label = m.get(stance.lower(), ("brass", stance))
    return f'<span class="rc-pill {tone}">{_html.escape(label)}</span>'


TYPE_LABELS = {
    "paper": "Research paper",
    "dataset": "Dataset",
    "github": "GitHub / project",
    "reimplementation": "GitHub / project",
    "news": "News",
    "venue": "Conference / venue",
    "conference": "Conference / venue",
    "author": "Researcher",
    "trend": "Trend",
    "trends": "Trend",
    "web": "Website",
    "other": "Other",
}


def type_tag(kind: str) -> str:
    key = (kind or "other").lower()
    label = TYPE_LABELS.get(key, kind.replace("_", " ").title() or "Other")
    return f'<span class="rc-tag">{_html.escape(label)}</span>'


def rating_pill(rating: str) -> str:
    key = (rating or "").lower()
    tone = {"high": "sage", "med": "brass", "medium": "brass", "low": "coral"}.get(key, "brass")
    return f'<span class="rc-pill {tone}">{_html.escape(rating)}</span>'


def summary_cards(items: list[dict]) -> None:
    cards = "".join(
        f'<div class="rc-card {_html.escape(str(i.get("tone", "neutral")))}">'
        f'<div class="k">{_html.escape(str(i.get("label", "")))}</div>'
        f'<div class="v">{_html.escape(str(i.get("value", "")))}</div>'
        f'<div class="n">{_html.escape(str(i.get("note", "")))}</div></div>'
        for i in items
    )
    st.markdown(f'<div class="rc-cards">{cards}</div>', unsafe_allow_html=True)


def score_ring(score: float, label: str = "Novelty score") -> None:
    p = max(0, min(100, int(round(score))))
    st.markdown(
        f'<div style="display:flex;flex-direction:column;align-items:center">'
        f'<div class="rc-ring" style="--p:{p}"><span>{p}</span></div>'
        f'<div class="rc-ring-label">{_html.escape(label)}</div></div>',
        unsafe_allow_html=True,
    )


def source_link(source_id: str, url: str | None = None) -> str:
    sid = _html.escape(source_id)
    href = safe_url(url)
    if href:
        return f'<a class="rc-src" href="{_html.escape(href, quote=True)}" target="_blank" rel="noopener">{sid}</a>'
    return f'<span class="rc-src">{sid}</span>'


def chat_bubble(role: str, text: str, source_chips_html: str = "") -> None:
    raw = role.lower()
    role = raw if raw in {"advocate", "skeptic", "judge"} else "judge"
    who = {"advocate": "Supporting position", "skeptic": "Contradicting position", "judge": "Conclusion"}.get(role, role)
    st.markdown(
        f'<div class="rc-chat"><div class="rc-msg {role}">'
        f'<div class="who">{_html.escape(who)}</div>{_html.escape(text)}'
        f'<div style="margin-top:.4rem">{source_chips_html}</div></div></div>',
        unsafe_allow_html=True,
    )


def unavailable_note() -> str:
    return f'<span class="rc-unavail">{_html.escape(UNAVAILABLE)}</span>'
