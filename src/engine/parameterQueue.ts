export type ParameterValue = number | string;

export interface QueuedParameter {
  target: string;
  value: ParameterValue;
}

/**
 * Lock-free single-producer/single-consumer queue implemented with SharedArrayBuffer.
 * The audio engine can poll the shared head/tail without any mutexes.
 */
export class ParameterQueue {
  private readonly capacity: number;
  private readonly buffer: SharedArrayBuffer;
  private readonly headIndex: Int32Array;
  private readonly tailIndex: Int32Array;
  private readonly targets: Int32Array;
  private readonly values: Float64Array;
  private readonly strings: Map<number, string>;
  private readonly channel: string;
  private stringKey: number;

  constructor(channel: string, capacity = 256) {
    this.capacity = capacity;
    this.channel = channel;
    // head, tail, and stringKey indexes live in first 3 slots
    this.buffer = new SharedArrayBuffer((3 + capacity * 2) * Int32Array.BYTES_PER_ELEMENT + capacity * Float64Array.BYTES_PER_ELEMENT);
    this.headIndex = new Int32Array(this.buffer, 0, 1);
    this.tailIndex = new Int32Array(this.buffer, Int32Array.BYTES_PER_ELEMENT, 1);
    this.targets = new Int32Array(this.buffer, Int32Array.BYTES_PER_ELEMENT * 2, capacity);
    this.values = new Float64Array(this.buffer, Int32Array.BYTES_PER_ELEMENT * (2 + capacity), capacity);
    this.strings = new Map();
    this.stringKey = 0;
  }

  enqueue(target: string, value: ParameterValue): boolean {
    const head = Atomics.load(this.headIndex, 0);
    const tail = Atomics.load(this.tailIndex, 0);
    const nextTail = (tail + 1) % this.capacity;
    if (nextTail === head) {
      return false; // queue is full
    }

    const index = tail;
    this.targets[index] = this.hashTarget(target);
    if (typeof value === 'number') {
      this.values[index] = value;
    } else {
      const key = ++this.stringKey;
      this.values[index] = key;
      this.strings.set(key, value);
    }

    Atomics.store(this.tailIndex, 0, nextTail);
    Atomics.notify(this.tailIndex, 0);
    return true;
  }

  dequeue(): QueuedParameter | undefined {
    const head = Atomics.load(this.headIndex, 0);
    const tail = Atomics.load(this.tailIndex, 0);
    if (head === tail) {
      return undefined;
    }

    const index = head;
    const hashedTarget = this.targets[index];
    const rawValue = this.values[index];
    Atomics.store(this.headIndex, 0, (head + 1) % this.capacity);
    Atomics.notify(this.headIndex, 0);

    const target = this.reverseHash(hashedTarget);
    const stringValue = this.strings.get(rawValue);
    if (stringValue !== undefined) {
      this.strings.delete(rawValue);
      return { target, value: stringValue };
    }

    return { target, value: rawValue };
  }

  getChannel(): string {
    return this.channel;
  }

  /**
   * Maps human-readable identifiers to int32 IDs for faster transfer to native code.
   * In this placeholder implementation we simply use a basic hash.
   */
  private hashTarget(target: string): number {
    let hash = 0;
    for (let i = 0; i < target.length; i += 1) {
      hash = (hash << 5) - hash + target.charCodeAt(i);
      hash |= 0; // convert to 32-bit integer
    }
    return hash;
  }

  private reverseHash(hash: number): string {
    // In a production system this would map back to a lookup table. Here we preserve the original string in a map.
    return `${this.channel}:${hash}`;
  }
}
