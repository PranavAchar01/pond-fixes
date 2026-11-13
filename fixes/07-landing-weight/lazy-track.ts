// Drop-in replacement for the eagerly loaded track chunk (PostHog, 282 KB raw).
// Components call track() as before; events queue in memory and PostHog loads
// after the page is idle or on the first interaction, whichever comes first.
type Props = Record<string, unknown>;
type Client = { capture(event: string, props?: Props): void };
type Loader = () => Promise<Client>;

export function createTracker(load: Loader, schedule: (fn: () => void) => void) {
  const queue: Array<[string, Props | undefined]> = [];
  let client: Client | null = null;
  let loading: Promise<void> | null = null;

  const start = () => {
    loading ??= load().then((c) => {
      client = c;
      for (const [e, p] of queue.splice(0)) c.capture(e, p);
    });
    return loading;
  };
  schedule(start);

  return {
    track(event: string, props?: Props) {
      if (client) client.capture(event, props);
      else queue.push([event, props]);
    },
    flush: start,
    pending: () => queue.length,
  };
}

// In the app:
// const idle = (fn: () => void) => {
//   const go = () => { removeEventListener("pointerdown", go); fn(); };
//   addEventListener("pointerdown", go, { once: true });
//   (window.requestIdleCallback ?? setTimeout)(go, { timeout: 3000 } as never);
// };
// export const { track } = createTracker(() => import("./posthog-client").then((m) => m.client), idle);
