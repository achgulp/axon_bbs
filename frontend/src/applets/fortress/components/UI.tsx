
import React from 'react';
import { Player, Unit, UnitType, UserInfo, WorldState } from '../types';
import { PLAYER_COLORS, UNIT_STATS } from '../constants';

interface UIProps {
  player: Player;
  opponent: UserInfo;
  worldState: WorldState;
  onBuildUnit: (unitType: UnitType) => void;
  selectedUnit: Unit | null;
}

const HealthBar: React.FC<{ health: number; maxHealth: number; color: string }> = ({ health, maxHealth, color }) => {
  const percentage = (health / maxHealth) * 100;
  return (
    <div className="w-full bg-gray-700 rounded-full h-2.5">
      <div className="h-2.5 rounded-full" style={{ width: `${percentage}%`, backgroundColor: color }}></div>
    </div>
  );
};

const UI: React.FC<UIProps> = ({ player, opponent, worldState, onBuildUnit, selectedUnit }) => {
  const playerFortress = worldState.fortresses.find(f => f.ownerId === player.id);
  const opponentFortress = worldState.fortresses.find(f => f.ownerId === (1 - player.id));
  const playerResources = Math.floor(worldState.resources[player.id]);

  return (
    <div className="absolute inset-0 pointer-events-none p-4 flex flex-col justify-between">
      {/* Top Bar: Player Info */}
      <div className="flex justify-between items-start text-lg">
        <div className="bg-black/50 p-3 rounded-lg w-1/4">
          <p className="font-bold" style={{ color: `#${player.color.toString(16)}` }}>{player.nickname} (You)</p>
          <p>Resources: <span className="font-mono">{playerResources}</span></p>
          {playerFortress && <HealthBar health={playerFortress.health} maxHealth={playerFortress.maxHealth} color={`#${player.color.toString(16)}`} />}
        </div>
        <div className="bg-black/50 p-3 rounded-lg w-1/4 text-right">
          {/* FIX: PLAYER_COLORS was not defined. It is now imported from constants. */}
          <p className="font-bold" style={{ color: `#${(PLAYER_COLORS[1 - player.id]).toString(16)}` }}>{opponent.nickname}</p>
          {opponentFortress ? (
            <>
              <p>Fortress Health</p>
              {/* FIX: PLAYER_COLORS was not defined. It is now imported from constants. */}
              <HealthBar health={opponentFortress.health} maxHealth={opponentFortress.maxHealth} color={`#${(PLAYER_COLORS[1 - player.id]).toString(16)}`} />
            </>
          ) : <p>Loading...</p>}
        </div>
      </div>

      {/* Bottom Bar: Build Menu and Unit Info */}
      <div className="flex justify-center items-end">
        <div className="bg-black/50 p-3 rounded-lg flex items-center space-x-4 pointer-events-auto">
          {selectedUnit ? (
            <div className="text-center w-64">
                <h3 className="text-lg font-bold">{selectedUnit.type}</h3>
                <HealthBar health={selectedUnit.health} maxHealth={selectedUnit.maxHealth} color={`#${player.color.toString(16)}`} />
                <p>{Math.ceil(selectedUnit.health)} / {selectedUnit.maxHealth} HP</p>
            </div>
          ) : (
            <>
              {(Object.keys(UNIT_STATS) as UnitType[]).map(unitType => {
                const stats = UNIT_STATS[unitType];
                const canAfford = playerResources >= stats.cost;
                return (
                  <button
                    key={unitType}
                    onClick={() => canAfford && onBuildUnit(unitType)}
                    disabled={!canAfford}
                    className={`p-4 rounded-lg text-left transition ${
                      canAfford
                        ? 'bg-gray-700 hover:bg-gray-600'
                        : 'bg-gray-800 text-gray-500 cursor-not-allowed'
                    }`}
                  >
                    <p className="font-bold text-lg">{unitType}</p>
                    <p className="text-sm">Cost: <span className="font-mono">{stats.cost}</span></p>
                  </button>
                );
              })}
            </>
          )}
        </div>
      </div>
    </div>
  );
};

export default UI;