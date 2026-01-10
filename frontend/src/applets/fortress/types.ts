
export enum GameState {
  Lobby = 'LOBBY',
  Game = 'GAME',
  GameOver = 'GAME_OVER',
}

export interface UserInfo {
  nickname: string;
  pubkey: string;
  isAI?: boolean;
}

export interface Player extends UserInfo {
  id: number; // 0 or 1
  color: number;
}

export enum UnitType {
  Tank = 'TANK',
  Drone = 'DRONE',
}

export interface Unit {
  id: string;
  ownerId: number;
  type: UnitType;
  position: { x: number; y: number; z: number };
  targetId: string | null;
  health: number;
  maxHealth: number;
  lastAttack?: number;
}

export interface Fortress {
  id: string;
  ownerId: number;
  position: { x: number; y: number; z: number };
  health: number;
  maxHealth: number;
}

export interface WorldState {
  fortresses: Fortress[];
  units: Unit[];
  resources: number[];
}

export enum GameEventType {
  JoinGame = 'JOIN_GAME',
  StartGame = 'START_GAME',
  BuildUnit = 'BUILD_UNIT',
  MoveUnit = 'MOVE_UNIT',
  UnitAttack = 'UNIT_ATTACK',
  GameOver = 'GAME_OVER',
  SyncState = 'SYNC_STATE',
}

export interface GameEvent {
  type: GameEventType;
  payload: any;
  timestamp: number;
  sender: UserInfo;
}

export interface BbsEvent {
  id: number;
  subject: string;
  body: string;
  author_nickname: string;
  pubkey: string;
}
