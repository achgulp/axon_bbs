
import React, { useRef, useEffect, useCallback } from 'react';
import * as THREE from 'three';
import { WorldState, Player, Unit, GameEventType, GameEvent } from '../types';
import { MAP_SIZE, PLAYER_COLORS, UNIT_STATS } from '../constants';
import { gameService } from '../services/gameService';

interface GameBoardProps {
  worldState: WorldState;
  setWorldState: React.Dispatch<React.SetStateAction<WorldState>>;
  player: Player;
  selectedUnit: Unit | null;
  onUnitSelect: (unit: Unit | null) => void;
}

const GameBoard: React.FC<GameBoardProps> = ({ worldState, setWorldState, player, selectedUnit, onUnitSelect }) => {
  const mountRef = useRef<HTMLDivElement>(null);
  const gameRef = useRef<{
    scene: THREE.Scene,
    camera: THREE.OrthographicCamera,
    renderer: THREE.WebGLRenderer,
    raycaster: THREE.Raycaster,
    mouse: THREE.Vector2,
    unitMap: Map<string, THREE.Object3D>,
    fortressMap: Map<string, THREE.Object3D>,
    ground: THREE.Mesh,
  } | null>(null);

  const handlePointerDown = useCallback((event: PointerEvent) => {
    if (!gameRef.current) return;
    const { raycaster, mouse, camera, scene } = gameRef.current;
    
    mouse.x = (event.clientX / window.innerWidth) * 2 - 1;
    mouse.y = -(event.clientY / window.innerHeight) * 2 + 1;
    
    raycaster.setFromCamera(mouse, camera);

    const intersects = raycaster.intersectObjects(scene.children, true);
    
    if (selectedUnit) {
      const groundIntersect = intersects.find(i => i.object.name === 'ground');
      if (groundIntersect) {
        const targetPosition = groundIntersect.point;
        
        // Find if an enemy was clicked
        const enemyIntersect = intersects.find(i => i.object.userData.type === 'unit' || i.object.userData.type === 'fortress');
        let targetId: string | null = null;
        if(enemyIntersect && enemyIntersect.object.userData.ownerId !== player.id) {
          targetId = enemyIntersect.object.userData.id;
        }

        const movePayload = {
          unitId: selectedUnit.id,
          targetPosition: { x: targetPosition.x, y: 0, z: targetPosition.z },
          targetId,
        };
        // Update local state immediately for responsiveness
        setWorldState(prev => ({
          ...prev,
          units: prev.units.map(u => u.id === selectedUnit.id ? { ...u, targetId } : u)
        }));
        
        // Post event for opponent
        gameService.postEvent({ type: GameEventType.MoveUnit, payload: movePayload }, player);
        onUnitSelect(null);
        return;
      }
    }
    
    const unitIntersect = intersects.find(i => i.object.userData.type === 'unit');
    if (unitIntersect) {
        const unit = worldState.units.find(u => u.id === unitIntersect.object.userData.id);
        if (unit) {
            onUnitSelect(unit);
            return;
        }
    }
    
    onUnitSelect(null);
  }, [onUnitSelect, selectedUnit, player, worldState.units, setWorldState]);

  useEffect(() => {
    if (!mountRef.current) return;

    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x1a2e40);
    const aspect = window.innerWidth / window.innerHeight;
    const d = MAP_SIZE.depth / 2 + 10;
    const camera = new THREE.OrthographicCamera(-d * aspect, d * aspect, d, -d, 1, 1000);
    camera.position.set(10, 30, 10);
    camera.lookAt(0, 0, 0);

    const renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setSize(window.innerWidth, window.innerHeight);
    renderer.shadowMap.enabled = true;
    mountRef.current.appendChild(renderer.domElement);

    const ambientLight = new THREE.AmbientLight(0xffffff, 0.5);
    scene.add(ambientLight);

    const directionalLight = new THREE.DirectionalLight(0xffffff, 0.8);
    directionalLight.position.set(10, 20, 5);
    directionalLight.castShadow = true;
    scene.add(directionalLight);

    const groundGeometry = new THREE.PlaneGeometry(MAP_SIZE.width, MAP_SIZE.depth);
    const groundMaterial = new THREE.MeshStandardMaterial({ color: 0x334155 });
    const ground = new THREE.Mesh(groundGeometry, groundMaterial);
    ground.rotation.x = -Math.PI / 2;
    ground.receiveShadow = true;
    ground.name = 'ground';
    scene.add(ground);
    
    gameRef.current = {
      scene, camera, renderer, 
      raycaster: new THREE.Raycaster(), 
      mouse: new THREE.Vector2(),
      unitMap: new Map(),
      fortressMap: new Map(),
      ground,
    };

    mountRef.current.addEventListener('pointerdown', handlePointerDown);
    
    const animate = () => {
        if (!gameRef.current) return;
        
        // Update logic
        setWorldState(prev => {
            const newState = { ...prev, units: [...prev.units], fortresses: [...prev.fortresses] };
            const dt = 1/60; // Assume 60fps for deterministic simulation

            newState.units.forEach(unit => {
                if (unit.targetId) {
                    const targetUnit = newState.units.find(u => u.id === unit.targetId);
                    const targetFortress = newState.fortresses.find(f => f.id === unit.targetId);
                    const target = targetUnit || targetFortress;

                    if (target) {
                        const unitPos = new THREE.Vector3(unit.position.x, unit.position.y, unit.position.z);
                        const targetPos = new THREE.Vector3(target.position.x, target.position.y, target.position.z);
                        const distance = unitPos.distanceTo(targetPos);
                        
                        const unitStats = UNIT_STATS[unit.type];
                        if (distance > unitStats.range) {
                           // Move towards target
                           const direction = targetPos.clone().sub(unitPos).normalize();
                           unit.position.x += direction.x * unitStats.speed * dt;
                           unit.position.z += direction.z * unitStats.speed * dt;
                        } else {
                           // Attack (This should be event-based, but for local simulation)
                           // Only player should emit attack events
                           if (unit.ownerId === player.id) {
                            // A simple cooldown mechanism would be needed here
                            gameService.postEvent({
                                type: GameEventType.UnitAttack,
                                payload: { attackerId: unit.id, targetId: target.id, damage: unitStats.damage }
                            }, player);
                           }
                        }
                    } else {
                        unit.targetId = null; // Target is gone
                    }
                }
            });

            return newState;
        });
        
        renderer.render(scene, camera);
        requestAnimationFrame(animate);
    };
    animate();

    const currentMount = mountRef.current;
    return () => {
      currentMount.removeChild(renderer.domElement);
      currentMount.removeEventListener('pointerdown', handlePointerDown);
    };
  }, [handlePointerDown, player, setWorldState]);

  // Update Three.js objects from worldState
  useEffect(() => {
    if (!gameRef.current) return;
    const { scene, unitMap, fortressMap } = gameRef.current;

    // Fortresses
    worldState.fortresses.forEach(fortress => {
      if (!fortressMap.has(fortress.id)) {
        const geometry = new THREE.BoxGeometry(6, 4, 6);
        const material = new THREE.MeshStandardMaterial({ color: PLAYER_COLORS[fortress.ownerId] });
        const mesh = new THREE.Mesh(geometry, material);
        mesh.position.set(fortress.position.x, 2, fortress.position.z);
        mesh.castShadow = true;
        mesh.userData = { id: fortress.id, type: 'fortress', ownerId: fortress.ownerId };
        scene.add(mesh);
        fortressMap.set(fortress.id, mesh);
      }
    });

    // Units
    const currentUnitIds = new Set(worldState.units.map(u => u.id));
    unitMap.forEach((mesh, id) => {
      if (!currentUnitIds.has(id)) {
        scene.remove(mesh);
        unitMap.delete(id);
      }
    });

    worldState.units.forEach(unit => {
      let mesh = unitMap.get(unit.id) as THREE.Mesh;
      if (!mesh) {
        const stats = UNIT_STATS[unit.type];
        const geometry = unit.type === 'TANK' ? new THREE.BoxGeometry(1, 0.5, 1.5) : new THREE.SphereGeometry(0.6, 16, 8);
        const material = new THREE.MeshStandardMaterial({ color: PLAYER_COLORS[unit.ownerId] });
        mesh = new THREE.Mesh(geometry, material);
        mesh.castShadow = true;
        mesh.userData = { id: unit.id, type: 'unit', ownerId: unit.ownerId };
        scene.add(mesh);
        unitMap.set(unit.id, mesh);
      }
      mesh.position.set(unit.position.x, 0.25, unit.position.z);
      
      // Visual selection highlight
      const isSelected = selectedUnit?.id === unit.id;
      (mesh.material as THREE.MeshStandardMaterial).emissive.setHex(isSelected ? 0xffff00 : 0x000000);
    });
  }, [worldState, selectedUnit]);

  return <div ref={mountRef} className="w-full h-full" />;
};

export default GameBoard;
