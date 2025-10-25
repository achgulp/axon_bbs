
import { UnitType, UserInfo } from './types';

export const AI_USER_INFO: UserInfo = {
  nickname: 'Fortress AI',
  pubkey: 'ai_opponent_pubkey_system_id',
  isAI: true,
};

export const GAME_SUBJECT = 'FORTRESS_OVERLORD_V1';

export const MAP_SIZE = { width: 40, depth: 50 };
export const PLAYER_COLORS = [0x007bff, 0xff4136]; // Blue, Red

export const FORTRESS_HEALTH = 2000;
export const STARTING_RESOURCES = 500;
export const RESOURCE_GENERATION_RATE = 2; // per second

export const UNIT_STATS = {
  [UnitType.Tank]: {
    cost: 100,
    health: 100,
    speed: 2.5,
    damage: 10,
    range: 1.5,
  },
  [UnitType.Drone]: {
    cost: 75,
    health: 50,
    speed: 4,
    damage: 5,
    range: 1,
  },
};
