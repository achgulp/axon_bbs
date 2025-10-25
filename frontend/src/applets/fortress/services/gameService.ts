
import { GAME_SUBJECT } from '../constants';
import { GameEvent, BbsEvent, UserInfo } from '../types';

let processedEventIds = new Set<number>();

export const gameService = {
  async postEvent(event: Omit<GameEvent, 'timestamp' | 'sender'>, senderInfo: UserInfo) {
    const fullEvent: GameEvent = {
      ...event,
      sender: senderInfo,
      timestamp: Date.now(),
    };
    try {
      await window.bbs.postEvent({
        subject: GAME_SUBJECT,
        body: JSON.stringify(fullEvent),
      });
    } catch (error) {
      console.error("Failed to post game event:", error);
    }
  },

  async pollEvents(callback: (event: GameEvent) => void) {
    try {
      const bbsEvents: BbsEvent[] = await window.bbs.readEvents();
      
      const newGameEvents = bbsEvents
        .filter(e => e.subject === GAME_SUBJECT && !processedEventIds.has(e.id))
        .sort((a, b) => a.id - b.id);

      for (const bbsEvent of newGameEvents) {
        processedEventIds.add(bbsEvent.id);
        try {
          const gameEvent: GameEvent = JSON.parse(bbsEvent.body);
          callback(gameEvent);
        } catch (parseError) {
          console.error("Failed to parse game event body:", parseError);
        }
      }
    } catch (error) {
      console.error("Failed to poll events:", error);
    }
  },

  startPolling(callback: (event: GameEvent) => void, interval = 1000) {
    const poll = () => {
      this.pollEvents(callback);
    };
    poll(); // Initial poll
    return setInterval(poll, interval);
  },

  stopPolling(intervalId: number) {
    clearInterval(intervalId);
    processedEventIds.clear();
  },
};
