
import React, { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import GameBoard from './GameBoard';
import UI from './UI';
import { WorldState, Player, Unit, Fortress, GameEvent, GameEventType, UnitType, UserInfo } from '../types';
import { gameService } from '../services/gameService';
import { MAP_SIZE, FORTRESS_HEALTH, STARTING_RESOURCES, RESOURCE_GENERATION_RATE, UNIT_STATS, AI_USER_INFO } from '../constants';
import { soundService } from '../services/soundService';

interface GameProps {
  player: Player;
  opponent: UserInfo;
  onGameOver: () => void;
}

const Game: React.FC<GameProps> = ({ player, opponent, onGameOver }) => {
  const initialWorldState: WorldState = useMemo(() => ({
    fortresses: [
      { id: 'fortress-0', ownerId: 0, position: { x: 0, y: 0, z: MAP_SIZE.depth / 2 - 2 }, health: FORTRESS_HEALTH, maxHealth: FORTRESS_HEALTH },
      { id: 'fortress-1', ownerId: 1, position: { x: 0, y: 0, z: -MAP_SIZE.depth / 2 + 2 }, health: FORTRESS_HEALTH, maxHealth: FORTRESS_HEALTH },
    ],
    units: [],
    resources: [STARTING_RESOURCES, STARTING_RESOURCES],
  }), []);

  const [worldState, setWorldState] = useState<WorldState>(initialWorldState);
  const [selectedUnit, setSelectedUnit] = useState<Unit | null>(null);
  const pollingId = useRef<number | null>(null);
  const resourceIntervalId = useRef<number | null>(null);
  const aiTickIntervalId = useRef<number | null>(null);

  const handleUnitSelect = useCallback((unit: Unit | null) => {
    if (unit && unit.ownerId === player.id) {
      setSelectedUnit(unit);
    } else {
      setSelectedUnit(null);
    }
  }, [player.id]);

  const handleBuildUnit = useCallback((unitType: UnitType) => {
    const unitCost = UNIT_STATS[unitType].cost;
    if (worldState.resources[player.id] >= unitCost) {
      const newUnitId = `${player.id}-${unitType}-${Date.now()}`;
      const spawnZ = player.id === 0 ? MAP_SIZE.depth / 2 - 5 : -MAP_SIZE.depth / 2 + 5;
      const spawnX = (Math.random() - 0.5) * (MAP_SIZE.width - 4);
      
      const buildPayload = {
        unitId: newUnitId,
        unitType: unitType,
        ownerId: player.id,
        position: { x: spawnX, y: 0, z: spawnZ }
      };
      
      gameService.postEvent({
        type: GameEventType.BuildUnit,
        payload: buildPayload
      }, player);
      
      setWorldState(prev => ({
        ...prev,
        resources: prev.resources.map((r, i) => i === player.id ? r - unitCost : r)
      }));

      soundService.playSound('build');
    }
  }, [player, worldState.resources]);

  const aiTick = useCallback(() => {
    if (!opponent.isAI) return;

    const aiPlayerId = 1 - player.id;
    const aiResources = worldState.resources[aiPlayerId];
    
    const canBuildTank = aiResources >= UNIT_STATS[UnitType.Tank].cost;
    const canBuildDrone = aiResources >= UNIT_STATS[UnitType.Drone].cost;
    
    if (canBuildTank || canBuildDrone) {
        const unitTypeToBuild = canBuildTank && Math.random() > 0.4 ? UnitType.Tank : canBuildDrone ? UnitType.Drone : null;

        if (unitTypeToBuild) {
            const newUnitId = `${aiPlayerId}-${unitTypeToBuild}-${Date.now()}`;
            const spawnZ = aiPlayerId === 0 ? MAP_SIZE.depth / 2 - 5 : -MAP_SIZE.depth / 2 + 5;
            const spawnX = (Math.random() - 0.5) * (MAP_SIZE.width - 4);

            const buildPayload = {
                unitId: newUnitId,
                unitType: unitTypeToBuild,
                ownerId: aiPlayerId,
                position: { x: spawnX, y: 0, z: spawnZ }
            };

            gameService.postEvent({
                type: GameEventType.BuildUnit,
                payload: buildPayload
            }, AI_USER_INFO);
        }
    }
    
    const idleAiUnits = worldState.units.filter(u => u.ownerId === aiPlayerId && u.targetId === null);
    const enemyFortress = worldState.fortresses.find(f => f.ownerId === player.id);

    if (idleAiUnits.length > 0 && enemyFortress) {
        idleAiUnits.forEach(unit => {
            const movePayload = {
                unitId: unit.id,
                targetId: enemyFortress.id,
                targetPosition: enemyFortress.position
            };
            gameService.postEvent({
                type: GameEventType.MoveUnit,
                payload: movePayload
            }, AI_USER_INFO);
        });
    }

  }, [opponent.isAI, player.id, worldState.resources, worldState.units, worldState.fortresses]);

  const handleGameEvent = useCallback((event: GameEvent) => {
    setWorldState(prev => {
        let newUnits = [...prev.units];
        let newFortresses = [...prev.fortresses];
        let newResources = [...prev.resources];

        switch(event.type) {
            case GameEventType.BuildUnit:
                const { unitId, unitType, ownerId, position } = event.payload;
                const stats = UNIT_STATS[unitType];
                if (!newUnits.some(u => u.id === unitId)) {
                    newUnits.push({
                        id: unitId,
                        ownerId,
                        type: unitType,
                        position,
                        targetId: null,
                        health: stats.health,
                        maxHealth: stats.health,
                        lastAttack: 0,
                    });
                     if (ownerId !== player.id) {
                         newResources = newResources.map((r, i) => i === ownerId ? r - stats.cost : r);
                     }
                }
                break;
            case GameEventType.MoveUnit:
                const { unitId: moveUnitId, targetId } = event.payload;
                newUnits = newUnits.map(u => {
                    if (u.id === moveUnitId) {
                        return { ...u, targetId };
                    }
                    return u;
                });
                break;
            case GameEventType.UnitAttack:
                const { attackerId, targetId: attackTargetId, damage } = event.payload;
                const attacker = newUnits.find(u => u.id === attackerId);
                const now = Date.now();

                if (attacker && now - (attacker.lastAttack || 0) > 1000) {
                    attacker.lastAttack = now;
                    let targetUnit = newUnits.find(u => u.id === attackTargetId);
                    let targetFortress = newFortresses.find(f => f.id === attackTargetId);

                    if (targetUnit) {
                        targetUnit.health -= damage;
                        if (targetUnit.health <= 0) {
                            newUnits = newUnits.filter(u => u.id !== attackTargetId);
                            soundService.playSound('explosion');
                        }
                    } else if (targetFortress) {
                        targetFortress.health -= damage;
                        if (targetFortress.health <= 0) {
                            const winner = newFortresses.find(f => f.id !== attackTargetId)?.ownerId;
                            if (winner !== undefined && event.sender.pubkey === player.pubkey) {
                                gameService.postEvent({ type: GameEventType.GameOver, payload: { winnerId: winner } }, player);
                            }
                        }
                    }
                }
                break;
            case GameEventType.GameOver:
                const { winnerId } = event.payload;
                const message = winnerId === player.id ? "You Won!" : "You Lost.";
                alert(message);
                onGameOver();
                break;
        }
        return { ...prev, units: newUnits, fortresses: newFortresses, resources: newResources };
    });
  }, [player, onGameOver]);

  useEffect(() => {
    pollingId.current = gameService.startPolling(handleGameEvent, 500);
    
    resourceIntervalId.current = window.setInterval(() => {
      setWorldState(prev => ({
        ...prev,
        resources: prev.resources.map(r => r + RESOURCE_GENERATION_RATE)
      }));
    }, 1000);

    if (opponent.isAI) {
        aiTickIntervalId.current = window.setInterval(aiTick, 2000); // AI makes decisions every 2 seconds
    }
    
    return () => {
      if (pollingId.current) gameService.stopPolling(pollingId.current);
      if (resourceIntervalId.current) clearInterval(resourceIntervalId.current);
      if (aiTickIntervalId.current) clearInterval(aiTickIntervalId.current);
    };
  }, [handleGameEvent, aiTick, opponent.isAI]);

  return (
    <div className="relative w-full h-full">
      <GameBoard 
        worldState={worldState}
        setWorldState={setWorldState}
        player={player}
        selectedUnit={selectedUnit}
        onUnitSelect={handleUnitSelect}
      />
      <UI 
        player={player} 
        opponent={opponent}
        worldState={worldState}
        onBuildUnit={handleBuildUnit}
        selectedUnit={selectedUnit}
      />
    </div>
  );
};

export default Game;
