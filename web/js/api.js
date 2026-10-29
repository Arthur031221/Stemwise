// Talks to the local Stemwise server, or falls back to the bundled demo when there is none.

export const STEMS = ["vocals", "drums", "bass", "guitar", "piano", "other"];

const here = (path) => new URL(path, document.baseURI).href;

export class Api {
  constructor() { this.mode = "demo"; this.info = null; }

  async detect() {
    const forced = new URLSearchParams(location.search).has("demo");
    if (forced || location.hostname.endsWith("github.io")) return this.mode;
    try {
      const res = await fetch(here("api/health"), { cache: "no-store" });
      const type = res.headers.get("content-type") || "";
      if (res.ok && type.includes("json")) {
        this.info = await res.json();
        this.mode = "server";
        return this.mode;
      }
    } catch { /* no server, static hosting */ }
    this.mode = "demo";
    return this.mode;
  }

  async songs() {
    if (this.mode === "server") return (await fetch(here("api/songs"))).json();
    const res = await fetch(here("demo/index.json"));
    return res.ok ? res.json() : [];
  }

  async song(id) {
    const url = this.mode === "server" ? `api/songs/${id}` : `demo/${id}/meta.json`;
    const res = await fetch(here(url));
    if (!res.ok) throw new Error(`song ${id}: ${res.status}`);
    return res.json();
  }

  stemUrl(id, stem) {
    return here(this.mode === "server" ? `api/songs/${id}/stems/${stem}.flac` : `demo/${id}/${stem}.m4a`);
  }

  exportUrl(id, kind, query = "") {
    return this.mode === "server" ? here(`api/songs/${id}/export/${kind}${query}`) : null;
  }

  upload(file, onProgress) {
    return new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest();
      xhr.open("POST", here(`api/songs?name=${encodeURIComponent(file.name)}`));
      xhr.upload.onprogress = (e) => e.lengthComputable && onProgress?.(e.loaded / e.total);
      xhr.onload = () => {
        if (xhr.status < 300) resolve(JSON.parse(xhr.responseText));
        else reject(new Error(errorText(xhr.responseText) || `upload failed (${xhr.status})`));
      };
      xhr.onerror = () => reject(new Error("upload failed"));
      xhr.send(file);
    });
  }

  async rename(id, title) {
    const res = await fetch(here(`api/songs/${id}`), { method: "PATCH", headers: { "content-type": "application/json" }, body: JSON.stringify({ title }) });
    if (!res.ok) throw new Error(errorText(await res.text()));
    return (await res.json()).title ?? title;
  }

  async remove(id) { await fetch(here(`api/songs/${id}`), { method: "DELETE" }); }
}

function errorText(body) {
  try { return JSON.parse(body).error || JSON.parse(body).detail || body; } catch { return body; }
}
