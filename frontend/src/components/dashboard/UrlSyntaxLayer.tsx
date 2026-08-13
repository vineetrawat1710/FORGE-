type UrlPart = {
  text: string
  className: string
}

function tokenize(value: string): UrlPart[] {
  const match = value.match(/^(https?:\/\/)([^/?#]*)([^?#]*)(\?[^#]*)?(#.*)?$/)
  const parts = match
    ? [
        { text: match[1], className: 'protocol' },
        { text: match[2], className: 'domain' },
        { text: match[3], className: 'path' },
        { text: match[4] || '', className: 'query' },
        { text: match[5] || '', className: 'query' },
      ]
    : [{ text: value, className: 'path' }]

  return parts.flatMap(part => {
    if (!part.text) return []
    const tokens: UrlPart[] = []
    const variable = /\{\{[^}]+\}\}/g
    let cursor = 0
    let found: RegExpExecArray | null
    while ((found = variable.exec(part.text))) {
      if (found.index > cursor) tokens.push({ text: part.text.slice(cursor, found.index), className: part.className })
      tokens.push({ text: found[0], className: 'environment' })
      cursor = found.index + found[0].length
    }
    if (cursor < part.text.length) tokens.push({ text: part.text.slice(cursor), className: part.className })
    return tokens
  })
}

export function UrlSyntaxLayer({ value }: { value: string }) {
  if (!value) return null
  return <div className="url-syntax-layer">{tokenize(value || 'https://').map((part, index) => <span key={`${part.className}-${index}`} className={`url-part ${part.className}`}>{part.text}</span>)}</div>
}
