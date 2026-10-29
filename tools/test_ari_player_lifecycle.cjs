// Run: node tools/test_ari_player_lifecycle.cjs path/to/assets/ari.js
// Focused DOM lifecycle simulation; not a substitute for browser/playback QA.
'use strict';
const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const script = fs.readFileSync(process.argv[2], 'utf8');
let checks = 0;
const check = (actual, expected, note) => { assert.equal(actual, expected, note); checks++; };
function setup() {
  const events = {}, documentEvents = {};
  let document;
  const node = () => ({
    children: [], attrs: {}, dataset: {}, open: false, textContent: '',
    classList: { add(){}, remove(){}, contains(){ return false; }, toggle(){} },
    setAttribute(k,v){ this.attrs[k]=v; },
    addEventListener(k,v){ (this.events ||= {})[k]=v; },
    replaceChildren(...children){ this.children=children; },
    append(...children){ this.children.push(...children); },
    focus(){ document.activeElement=this; },
    showModal(){ this.open=true; }, close(){ this.open=false; },
    querySelector(){ return node(); }, querySelectorAll(){ return []; },
  });
  const selectors = Object.fromEntries([
    '#toast', '#burger', '#menu', '#movieDialog', '#moviePlayer',
    '#movieDialogTitle', '[data-close]', '#savedDialog', '#savedList',
    '[data-close-saved]', 'meta[name="theme-color"]',
  ].map(s=>[s,node()]));
  const play = node(); play.dataset.play='DdmpQrpSL3C';
  const trigger = node();
  document = {
    documentElement: { dataset:{} }, body:node(), activeElement:trigger, hidden:false,
    querySelector:s=>selectors[s]||null,
    querySelectorAll:s=>s==='[data-play]'?[play]:[],
    createElement:()=>node(), addEventListener:(k,v)=>documentEvents[k]=v,
  };
  const media = [{id:'DdmpQrpSL3C',title:'Get ready with me.',url:'https://www.instagram.com/ari1of1/reel/DdmpQrpSL3C/'}];
  const context = {
    document, window:{ARI_MEDIA:media}, matchMedia:()=>({matches:false}),
    localStorage:{getItem:()=>null,setItem(){}},
    addEventListener:(k,v)=>events[k]=v,
    setTimeout:()=>0, clearTimeout(){}, navigator:{}, location:{href:'https://ari1of1.pages.dev/'},
  };
  vm.runInNewContext(script,context);
  return {events,documentEvents,selectors,play,trigger,document};
}
const h=setup(), dialog=h.selectors['#movieDialog'], slot=h.selectors['#moviePlayer'];
check(slot.children.length,0,'Players remain lazy before interaction');
check(dialog.open,false,'Player starts closed');
h.play.onclick();
check(dialog.open,true,'Click opens the player');
check(slot.children.length,3,'One iframe, explanatory note, and original-post link');
check(slot.children[0].src,'https://www.instagram.com/reel/DdmpQrpSL3C/embed/','Official embed URL');
check(slot.children[2].href,'https://www.instagram.com/ari1of1/reel/DdmpQrpSL3C/','Original-post fallback preserved');
h.events.pagehide({persisted:true});
check(slot.children.length,0,'Navigation unloads third-party media');
check(dialog.open,false,'Navigation must close the player, not leave an empty modal');
h.events.pageshow({persisted:true});
check(dialog.open,false,'Back/Forward restoration has no empty modal');
check(slot.children.length,0,'Restoration does not load media without interaction');
h.events.pagehide({persisted:true});
check(dialog.open,false,'Repeated navigation cleanup is idempotent');
h.play.onclick();
check(dialog.open,true,'Player can reopen after restoration');
check(slot.children.length,3,'Reopening creates only one fresh player');
h.selectors['[data-close]'].onclick();
check(dialog.open,false,'Visible Close still works');
check(slot.children.length,0,'Close unloads media');
check(h.document.activeElement,h.trigger,'Close returns focus to the opener');
h.play.onclick(); h.document.hidden=true; h.documentEvents.visibilitychange();
check(dialog.open,false,'Backgrounding still closes playback');
check(slot.children.length,0,'Backgrounding removes iframe');
h.document.hidden=false; h.play.onclick();
dialog.events.click({target:dialog});
check(dialog.open,false,'Backdrop close still works');
check(slot.children.length,0,'Backdrop close removes iframe');
h.play.onclick(); dialog.events.cancel(); dialog.close();
check(slot.children.length,0,'Native Escape cancellation removes iframe');
console.log(JSON.stringify({checks,passed:true,browser_qa:false}));
