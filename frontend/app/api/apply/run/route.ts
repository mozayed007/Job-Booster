import { API_URL, TOKEN_COOKIE, getServerToken, clearCookieHeader } from "@/lib/api/server";

export const runtime = "nodejs";

function unauthorized(): Response {
  const res = Response.json({ detail: "Session expired" }, { status: 401 });
  res.headers.append("Set-Cookie", clearCookieHeader(TOKEN_COOKIE));
  return res;
}

/**
 * Single backend entry point for the Apply page. The page posts a resume
 * (either an uploaded file or pasted text) plus a job description; we forward
 * to the backend's unified /pipeline/apply/file, which parses, tailors, writes
 * the cover letter, runs analysis, and tracks the application in one pass.
 * Pasted text is wrapped as a .txt so the file endpoint handles both inputs
 * identically and the cover-letter step always runs when the backend succeeds.
 */
export async function POST(req: Request) {
  const token = await getServerToken();
  if (!token) return unauthorized();

  const form = await req.formData();
  const jobText = String(form.get("jobText") ?? "");
  const file = form.get("file");
  const resumeText = String(form.get("resumeText") ?? "");

  if (!jobText.trim()) {
    return Response.json({ detail: "Paste a job description" }, { status: 400 });
  }

  let upload: Blob;
  let filename: string;
  if (file instanceof File) {
    upload = file;
    filename = file.name || "resume.txt";
  } else if (resumeText.trim()) {
    upload = new Blob([resumeText], { type: "text/plain" });
    filename = "pasted-resume.txt";
  } else {
    return Response.json({ detail: "Add a resume first" }, { status: 400 });
  }

  const out = new FormData();
  out.append("file", upload, filename);
  out.append("job_text", jobText);

  const upstream = await fetch(`${API_URL}/api/pipeline/apply/file`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
    body: out,
  });
  if (upstream.status === 401) return unauthorized();

  const text = await upstream.text();
  return new Response(text || null, {
    status: upstream.status,
    headers: {
      "Content-Type": upstream.headers.get("content-type") ?? "application/json",
    },
  });
}
