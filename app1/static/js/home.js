
(function(){
  "use strict";


  /* ------------------------------------------------------------
     Draws a smooth curved connector between the mentor and
     learner cards, re-measuring on every resize so it always
     meets the card edges — no matter the breakpoint.
  ------------------------------------------------------------ */
  const stage   = document.getElementById('heroVisual');
  const svg     = document.getElementById('connectorSvg');
  const path    = document.getElementById('connectorPath');
  const glow    = document.getElementById('connectorGlow');
  const mentor  = document.getElementById('mentorCard');
  const learner = document.getElementById('learnerCard');


  function edgePoint(card, side){
    const stageBox = stage.getBoundingClientRect();
    const cardBox  = card.getBoundingClientRect();
    const y = (cardBox.top - stageBox.top) + cardBox.height / 2;
    const x = side === 'right'
      ? (cardBox.left - stageBox.left) + cardBox.width
      : (cardBox.left - stageBox.left);
    return { x, y };
  }


  function drawConnector(){
    const stageBox = stage.getBoundingClientRect();
    svg.setAttribute('viewBox', `0 0 ${stageBox.width} ${stageBox.height}`);


    const start = edgePoint(mentor, 'right');
    const end   = edgePoint(learner, 'left');


    // Control points pulled outward for an elegant, open curve
    const dx = end.x - start.x;
    const c1x = start.x + dx * 0.35;
    const c1y = start.y - Math.abs(dx) * 0.08;
    const c2x = start.x + dx * 0.65;
    const c2y = end.y + Math.abs(dx) * 0.08;


    const d = `M ${start.x} ${start.y} C ${c1x} ${c1y}, ${c2x} ${c2y}, ${end.x} ${end.y}`;
    path.setAttribute('d', d);
    glow.setAttribute('d', d);
  }


  let resizeTimer;
  function scheduleRedraw(){
    cancelAnimationFrame(resizeTimer);
    resizeTimer = requestAnimationFrame(drawConnector);
  }


  window.addEventListener('resize', scheduleRedraw);
  window.addEventListener('load', drawConnector);


  // Redraw whenever the floating cards change position (their
  // CSS animation moves them without firing a resize event).
  if ('ResizeObserver' in window){
    new ResizeObserver(scheduleRedraw).observe(stage);
  }
  // Keep the curve locked on during the float animation.
  setInterval(drawConnector, 350);


  drawConnector();


  /* ------------------------------------------------------------
     Lightweight session clock, purely decorative — counts up
     to sell the "live" feeling without any external dependency.
  ------------------------------------------------------------ */
  const clockEl = document.getElementById('sessionClock');
  let seconds = 5 * 60 + 39;
  setInterval(function(){
    seconds++;
    const m = String(Math.floor(seconds / 60)).padStart(2, '0');
    const s = String(seconds % 60).padStart(2, '0');
    clockEl.textContent = `${m}:${s}`;
  }, 1000);
})();

