<style>
.js-plotly-plot .barlayer .point path{transform-box:fill-box;transform-origin:50% 100%;
  animation:barY .75s cubic-bezier(.6,0,.25,1) both;filter:drop-shadow(0 3px 4px rgba(19,42,84,.18))}
.js-plotly-plot .barlayer .point text{animation:barTxt .4s ease both}
@keyframes barY{from{transform:scaleY(0)}to{transform:none}}
@keyframes barX{from{transform:scaleX(0)}to{transform:none}}
@keyframes barTxt{from{opacity:0}to{opacity:1}}
/* 가로 막대(칸 키 hb_ · hbd_ — kdesign.hbar_key) — 바닥에서 자라지 않고 왼쪽에서 오른쪽으로 뻗는다.
   hbd_ = 가운데 0 에서 양쪽으로 갈리는 차트: 첫 계열(왼쪽으로 가는 막대)은 오른쪽 끝(0 자리)에서 왼쪽으로 뻗는다 */
[class*="st-key-hb_"] .js-plotly-plot .barlayer .point path,[class*="st-key-hbd_"] .js-plotly-plot .barlayer .point path{transform-origin:0 50%;animation-name:barX}
[class*="st-key-hbd_"] .js-plotly-plot .barlayer .trace:first-child .point path{transform-origin:100% 50%}
.js-plotly-plot .scatterlayer .trace:has(.js-line){animation:lineIn 1.5s cubic-bezier(.65,0,.35,1) both}
.js-plotly-plot .scatterlayer .trace:nth-child(2):has(.js-line){animation-delay:.18s}
.js-plotly-plot .scatterlayer .trace:nth-child(3):has(.js-line){animation-delay:.36s}
.js-plotly-plot .scatterlayer .js-line{filter:drop-shadow(0 5px 5px rgba(43,110,246,.28))}
@keyframes lineIn{from{clip-path:inset(-20px 100% -20px -20px)}to{clip-path:inset(-20px -20px -20px -20px)}}
${_STAGGER}
</style>