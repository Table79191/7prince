(async () => {
  await window.SEVEN_PRINCE_MANIFEST_READY;
  const files = ["app-parts/01.txt","app-parts/02.txt","app-parts/03.txt","app-parts/04.txt","app-parts/05.txt","app-parts/06.txt"];
  const parts = [];
  for (const file of files) {
    const r = await fetch(file, {cache:"no-store"});
    if (!r.ok) throw new Error(`${file}: ${r.status}`);
    parts.push(await r.text());
  }
  (0, eval)(parts.join(""));
})().catch(error => { console.error("7왕자 앱 로드 실패", error); });
