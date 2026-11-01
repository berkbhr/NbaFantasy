// Bounded workers, URL deduplication and shared pacing. No automatic retries.
function createYahooReadSession({maxPages=96,concurrency=2,minDelayMs=400}={}) {
  if(!Number.isInteger(maxPages) || maxPages<1 || maxPages>128 || ![1,2].includes(concurrency) || minDelayMs<400) throw new Error('Invalid Yahoo read budget');
  const nativeFetch=globalThis.fetch.bind(globalThis);
  let stopped=false, count=0, last=0, nextWorker=0;
  const workers=Array.from({length:concurrency},()=>Promise.resolve()), controllers=new Set();
  const responses=new Map();
  const metrics={requests:0,cache_hits:0,network_errors:0,http_errors:0,denials:0};
  const denied=/request denied|access denied|too many requests|verify you are human|captcha/i;
  if (globalThis.__nbaYahooReaderUntil>Date.now()) throw new Error('Yahoo okuyucusu zaten çalışıyor; ikinci tarama başlatılmadı.');
  const owner={};
  if(globalThis.__nbaYahooReaderOwner) throw new Error('Yahoo okuyucusu zaten çalışıyor.');
  globalThis.__nbaYahooReaderOwner=owner;
  const blocked=()=>{try{return sessionStorage.getItem('nbaYahooReaderBlocked')==='1';}catch(_){return true;}};
  function stop(persist=false) {stopped=true;for(const controller of controllers) controller.abort();if(persist){metrics.denials++;try{sessionStorage.setItem('nbaYahooReaderBlocked','1');}catch(_){}} }
  function guardedFetch(input,options={}) {
    const url=new URL(input,location.origin);
    const cacheKey=(options.method || 'GET').toUpperCase()==='GET' ? url.href : null;
    if(cacheKey && responses.has(cacheKey)) {metrics.cache_hits++;return responses.get(cacheKey).then(response=>response.clone());}
    const run=async()=>{
      if(stopped || blocked()) throw new Error('Yahoo okuması durduruldu; engel varken tekrar denenmez.');
      if(url.origin!==location.origin) return nativeFetch(input,options);
      if(denied.test(document.title+' '+(document.body?.innerText || '').slice(0,4000))) {stop(true);throw new Error('Yahoo erişimi reddediyor; okuma başlatılmadı.');}
      if(++count>maxPages) {stopped=true;throw new Error(`Tek çalıştırmanın ${maxPages} sayfalık okuma sınırına ulaşıldı.`);}
      const wait=Math.max(0,last+minDelayMs-Date.now());
      last=Date.now()+wait;
      if(wait) await new Promise(resolve=>setTimeout(resolve,wait));
      if(stopped || blocked()) throw new Error('Yahoo okuması durduruldu.');
      let response;
      const controller=new AbortController(), timer=setTimeout(()=>controller.abort(),12000);
      controllers.add(controller);
      const cancel=()=>controller.abort();
      if(options.signal) {if(options.signal.aborted) controller.abort();else options.signal.addEventListener('abort',cancel,{once:true});}
      try {
      metrics.requests++;
      response=await nativeFetch(input,{...options,cache:'default',signal:controller.signal});
      if(denied.test((await response.clone().text()).slice(0,12000))) {stop(true);throw new Error('Yahoo engel sayfası döndürdü; tüm okumalar durduruldu.');}
      if(!response.ok) {metrics.http_errors++;stop([401,403,429].includes(response.status));throw new Error(`Yahoo HTTP ${response.status}; bu çalıştırma durduruldu.`);}
      return response;
      }
      catch(error) {if(!stopped) metrics.network_errors++;stop();throw error;}
      finally {clearTimeout(timer);controllers.delete(controller);options.signal?.removeEventListener('abort',cancel);}
    };
    const worker=nextWorker++%workers.length;
    const result=workers[worker].then(run);workers[worker]=result.catch(()=>{});
    if(cacheKey) responses.set(cacheKey,result);
    return result.then(response=>response.clone());
  };
  guardedFetch.finish=()=>{stopped=true;for(const controller of controllers) controller.abort();if(globalThis.__nbaYahooReaderOwner===owner) delete globalThis.__nbaYahooReaderOwner;};
  guardedFetch.metrics=()=>({...metrics});
  return guardedFetch;
}
if(typeof module==='object') module.exports={createYahooReadSession};
