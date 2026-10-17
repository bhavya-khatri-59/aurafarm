export type ServerEvent = { event: string; data: any };

/**
 * Incrementally parses a text/event-stream. Feed it decoded chunks; it returns the complete events
 * and keeps any partial event buffered until the next chunk.
 */
export class SSEParser {
  private buffer = '';

  push(chunk: string): ServerEvent[] {
    this.buffer += chunk.replace(/\r\n/g, '\n');
    const events: ServerEvent[] = [];
    let boundary: number;
    while ((boundary = this.buffer.indexOf('\n\n')) !== -1) {
      const block = this.buffer.slice(0, boundary);
      this.buffer = this.buffer.slice(boundary + 2);
      let event = 'message';
      const dataLines: string[] = [];
      for (const line of block.split('\n')) {
        if (line.startsWith('event:')) event = line.slice(6).trim();
        else if (line.startsWith('data:')) dataLines.push(line.slice(5).trimStart());
      }
      if (dataLines.length) events.push({ event, data: JSON.parse(dataLines.join('\n')) });
    }
    return events;
  }
}
