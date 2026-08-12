window.SEVEN_PRINCE_MANIFEST_READY = (async () => {
  const files = ["manifest-parts/01.txt","manifest-parts/02.txt","manifest-parts/03.txt","manifest-parts/04.txt"];
  const parts = [];
  for (const file of files) {
    const r = await fetch(file, {cache:"no-store"});
    if (!r.ok) throw new Error(`${file}: ${r.status}`);
    parts.push(await r.text());
  }
  document.getElementById("embeddedImages").textContent = parts.join("");
})();
