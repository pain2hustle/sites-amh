const fs=require('node:fs');const vm=require('node:vm');const assert=require('node:assert/strict');const path=require('node:path');
const file=path.resolve(__dirname,'../../isatobaa/site/assets/age-confirmation.js');
const src=fs.readFileSync(file,'utf8');
const logic=src.slice(src.indexOf('  function adult('),src.indexOf('  function intercept('));
const context={URL,assert};vm.runInNewContext(`
const location={href:'https://isatobaa.pages.dev/'};
const parameter='amh-age-link';const platforms=new Map([['onlyfans.com','OnlyFans']]);const exactRestricted=new Map();const destinations=new WeakMap();const known=new Set();
${logic}
let writes=0;const attrs={'data-age-destination':'https://onlyfans.com/example',href:'https://onlyfans.com/example'};
const anchor={getAttribute:k=>attrs[k]??null,setAttribute:(k,v)=>{writes++;attrs[k]=v},get href(){return attrs.href}};
const first=protect(anchor);assert.equal(writes,1);assert.equal(first.url,'https://onlyfans.com/example');
for(let i=0;i<100;i++)assert.equal(protect(anchor).url,first.url);
assert.equal(writes,1,'repeated mutation scans must not rewrite unchanged href');
assert.equal(new URL(attrs.href).origin,'https://isatobaa.pages.dev');
assert.equal(new URL(attrs.href).searchParams.get(parameter),first.url);
attrs['data-age-destination']='https://onlyfans.com/changed';protect(anchor);assert.equal(writes,2);assert.equal(new URL(attrs.href).searchParams.get(parameter),'https://onlyfans.com/changed');
`,context,{timeout:1000});
console.log(JSON.stringify({test:'age-link observer idempotence',passed:true,repeatScans:100,unchangedHrefWrites:0,changedDestinationProtected:true}));
