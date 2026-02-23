import type { MemoryItem } from "../api";

function formatDate(dateStr: string): string {
  const [y, m, d] = dateStr.split("-").map(Number);
  const date = new Date(y, m - 1, d);
  return date.toLocaleDateString("en-US", {
    weekday: "short",
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

function renderInlineMarkdown(text: string): string {
  let html = text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
  // markdown links [text](url)
  html = html.replace(
    /\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g,
    '<a href="$2" target="_blank" rel="noopener">$1</a>',
  );
  // bare URLs
  html = html.replace(
    /(?<!href="|">)(https?:\/\/\S+?)(?=[)<\s]|$)/g,
    '<a href="$1" target="_blank" rel="noopener">$1</a>',
  );
  return html;
}

function attachmentLabel(url: string): string {
  try {
    const path = decodeURIComponent(new URL(url).pathname);
    return path.split("/").pop() || "attachment";
  } catch {
    return "attachment";
  }
}

export function MemoryCard({ memory }: { memory: MemoryItem }) {
  const title = memory.title || memory.content;
  const meta: string[] = [];
  if (memory.target) meta.push(formatDate(memory.target));
  if (memory.time) meta.push(memory.time);
  if (memory.place) meta.push(memory.place);

  const hasDetails =
    meta.length > 0 ||
    (memory.title && memory.content) ||
    (memory.attachments && memory.attachments.length > 0);

  if (!hasDetails) {
    return (
      <li className="memory-card">
        <strong
          dangerouslySetInnerHTML={{ __html: renderInlineMarkdown(title) }}
        />
      </li>
    );
  }

  return (
    <li className="memory-card">
      <details>
        <summary>
          <strong
            dangerouslySetInnerHTML={{ __html: renderInlineMarkdown(title) }}
          />
        </summary>
        {meta.length > 0 && <p>{meta.join(" \u00b7 ")}</p>}
        {memory.title && memory.content && (
          <div
            dangerouslySetInnerHTML={{
              __html: renderInlineMarkdown(memory.content),
            }}
          />
        )}
        {memory.attachments && memory.attachments.length > 0 && (
          <div className="attachments">
            Attachments:{" "}
            {memory.attachments.map((url) => (
              <a
                key={url}
                href={url}
                target="_blank"
                rel="noopener noreferrer"
              >
                {attachmentLabel(url)}
              </a>
            ))}
          </div>
        )}
      </details>
    </li>
  );
}
