-- | FogMesh — multi-agent fog layer with propagation.
--
-- FogMesh is an immutable value — a map from agent ID to FogMap.
-- All operations are pure: pass current POSIX time where decay is needed.
--
-- Propagation rule: when agent A lifts fog on key X, all agents holding
-- 'InferredUnknown' on X have their confidence halved. The topological
-- inference that X is universally unknown no longer holds.
--
-- The 'darkCore' is what no internal propagation can touch — gaps present
-- in every agent. External signal required to clear them.
module Fog.Mesh
  ( FogMesh(..)
  , emptyMesh
  , registerAgent
  , propagateLift
  , totalFogVolume
  , systemFogVolume
  , systemEntropy
  , unionGaps
  , darkCore
  , seamMatrix
  , highestTensionSeam
  , meshSnapshot
  , MeshSnapshot(..)
  ) where

import Data.Map.Strict (Map)
import qualified Data.Map.Strict as Map
import Data.Set (Set)
import qualified Data.Set as Set
import Data.List (maximumBy)
import Data.Ord (comparing)
import Fog.Gap (GapKind(..), Gap(..), effectiveConfidence)
import Fog.Map (FogMap(..), fogKeys, fogVolume, fogEntropy)
import Fog.Seam (FogSeam, measure, tension)

-- | A mesh of agents' fog maps.
data FogMesh = FogMesh
  { meshAgents   :: Map String FogMap
  , meshHalfLife :: Double
  } deriving (Eq, Show)

-- | Empty mesh.
emptyMesh :: Double -> FogMesh
emptyMesh hl = FogMesh { meshAgents = Map.empty, meshHalfLife = hl }

-- | Register an agent's fog map.
registerAgent :: FogMap -> FogMesh -> FogMesh
registerAgent fmap mesh =
  mesh { meshAgents = Map.insert (fogAgentId fmap) fmap (meshAgents mesh) }
  where fogAgentId = \f -> case f of FogMap aid _ -> aid

-- | Propagate a fog lift from @agentId@ on @key@.
--
-- For every other agent holding 'InferredUnknown' on the same key,
-- multiply their confidence by @factor@ (typically 0.5).
-- Returns the updated mesh and the list of agent IDs that were updated.
propagateLift
  :: String      -- ^ Agent lifting fog
  -> String      -- ^ Gap key (already full key, or pass domain separately)
  -> Double      -- ^ Propagation factor (e.g. 0.5)
  -> FogMesh
  -> (FogMesh, [String])
propagateLift agentId key factor mesh =
  let (updatedAgents, touched) =
        Map.foldlWithKey' step (meshAgents mesh, []) (meshAgents mesh)
  in (mesh { meshAgents = updatedAgents }, reverse touched)
  where
    step (agents, acc) aid fmap
      | aid == agentId = (agents, acc)
      | otherwise =
          case Map.lookup key (fogGaps fmap) of
            Just gap | gapKind gap == InferredUnknown ->
              let newGap   = gap { gapConfidence = max (gapConfidence gap * factor) 0.0 }
                  newFmap  = fmap { fogGaps = Map.insert key newGap (fogGaps fmap) }
              in (Map.insert aid newFmap agents, aid : acc)
            _ -> (agents, acc)

-- | Sum of all effective confidences across all agents (not deduplicated).
totalFogVolume :: Double -> FogMesh -> Double
totalFogVolume now mesh =
  Map.foldl' (\acc fmap -> acc + fogVolume now (meshHalfLife mesh) fmap) 0.0 (meshAgents mesh)

-- | Deduplicated fog volume: each gap key counted once at max confidence.
systemFogVolume :: Double -> FogMesh -> Double
systemFogVolume now mesh =
  let hl  = meshHalfLife mesh
      maxByKey = Map.foldl'
        (\acc fmap ->
           Map.foldlWithKey' (\m k gap ->
             let e = effectiveConfidence now hl gap
             in Map.insertWith max k e m
           ) acc (fogGaps fmap)
        ) Map.empty (meshAgents mesh)
  in Map.foldl' (+) 0.0 maxByKey

-- | Shannon entropy of the total mesh fog distribution.
systemEntropy :: Double -> FogMesh -> Double
systemEntropy now mesh =
  let hl   = meshHalfLife mesh
      effs = [ effectiveConfidence now hl gap
             | fmap <- Map.elems (meshAgents mesh)
             , gap  <- Map.elems (fogGaps fmap) ]
      total = sum effs
  in if total == 0.0
     then 0.0
     else negate $ sum [ let p = e / total in if p > 0 then p * logBase 2 p else 0.0
                       | e <- effs ]

-- | All gap keys present in any agent.
unionGaps :: FogMesh -> Set String
unionGaps mesh =
  Map.foldl' (\acc fmap -> Set.union acc (fogKeys fmap)) Set.empty (meshAgents mesh)

-- | Gaps present in ALL agents — genuine system-wide blind spots.
-- External signal required to clear these.
darkCore :: FogMesh -> Set String
darkCore mesh =
  case Map.elems (meshAgents mesh) of
    []     -> Set.empty
    (f:fs) -> foldl (\acc fmap -> Set.intersection acc (fogKeys fmap)) (fogKeys f) fs

-- | All pairwise seams.
seamMatrix :: Double -> FogMesh -> Map (String, String) FogSeam
seamMatrix now mesh =
  let hl     = meshHalfLife mesh
      agents = Map.elems (meshAgents mesh)
      pairs  = [ (a, b) | (a:rest) <- tails agents, b <- rest ]
  in Map.fromList
       [ ((fogAgentIdOf a, fogAgentIdOf b), measure now hl a b) | (a, b) <- pairs ]
  where
    fogAgentIdOf (FogMap aid _) = aid
    tails []     = []
    tails (x:xs) = (x:xs) : tails xs

-- | Which pair of agents has the most to offer each other?
highestTensionSeam :: Double -> FogMesh -> Maybe FogSeam
highestTensionSeam now mesh =
  let matrix = seamMatrix now mesh
  in if Map.null matrix
     then Nothing
     else Just . snd . maximumBy (comparing (tension . snd)) . Map.toList $ matrix

-- | Summary of the current mesh state.
data MeshSnapshot = MeshSnapshot
  { snapshotAgents        :: Int
  , snapshotTotalVolume   :: Double
  , snapshotSystemVolume  :: Double
  , snapshotSystemEntropy :: Double
  , snapshotUnionGaps     :: Int
  , snapshotDarkCore      :: Int
  } deriving (Eq, Show)

meshSnapshot :: Double -> FogMesh -> MeshSnapshot
meshSnapshot now mesh = MeshSnapshot
  { snapshotAgents        = Map.size (meshAgents mesh)
  , snapshotTotalVolume   = roundAt3 (totalFogVolume  now mesh)
  , snapshotSystemVolume  = roundAt3 (systemFogVolume now mesh)
  , snapshotSystemEntropy = roundAt3 (systemEntropy   now mesh)
  , snapshotUnionGaps     = Set.size (unionGaps mesh)
  , snapshotDarkCore      = Set.size (darkCore  mesh)
  }
  where
    roundAt3 x = fromIntegral (round (x * 1000) :: Int) / 1000.0
