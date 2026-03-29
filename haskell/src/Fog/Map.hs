-- | FogMap — the shape of what an agent doesn't know.
--
-- FogMap is an immutable value. All operations return new maps.
-- The type system makes mutation impossible — fog states are snapshots.
module Fog.Map
  ( FogMap(..)
  , emptyFog
  , addGap
  , removeGap
  , lookupGap
  , fogSize
  , fogKeys
  , fullKey
  ) where

import Data.Map.Strict (Map)
import qualified Data.Map.Strict as Map
import Data.Set (Set)
import qualified Data.Set as Set
import Fog.Gap

-- | Immutable snapshot of an agent's ignorance.
data FogMap = FogMap
  { fogAgentId :: String
  , fogGaps    :: Map String Gap
  } deriving (Eq, Show)

-- | Empty fog map for an agent.
emptyFog :: String -> FogMap
emptyFog agentId = FogMap { fogAgentId = agentId, fogGaps = Map.empty }

-- | Add a gap. Returns a new FogMap.
-- If the key already exists, the gap is left unchanged (already dark there).
addGap :: Gap -> FogMap -> FogMap
addGap gap fog =
  let k = fullKey (gapKey gap) (gapDomain gap)
  in fog { fogGaps = Map.insertWith (\_new old -> old) k gap (fogGaps fog) }

-- | Remove a gap (fog lifted). Returns the new map and whether anything changed.
removeGap :: String -> Maybe String -> FogMap -> (FogMap, Bool)
removeGap key domain fog =
  let k = fullKey key domain
  in if Map.member k (fogGaps fog)
     then (fog { fogGaps = Map.delete k (fogGaps fog) }, True)
     else (fog, False)

-- | Look up a specific gap.
lookupGap :: String -> Maybe String -> FogMap -> Maybe Gap
lookupGap key domain fog = Map.lookup (fullKey key domain) (fogGaps fog)

-- | Number of gaps.
fogSize :: FogMap -> Int
fogSize = Map.size . fogGaps

-- | All gap keys as a Set.
fogKeys :: FogMap -> Set String
fogKeys = Map.keysSet . fogGaps

-- | Build the canonical key from a key and optional domain.
fullKey :: String -> Maybe String -> String
fullKey key Nothing       = key
fullKey key (Just domain) = domain <> ":" <> key
