-- | Detect epistemic arbitrage across a mesh of agents.
module Fog.Detect.Arbitrage
  ( detectArbitrage
  , systemFogChange
  ) where

import Fog.Map (FogMap)
import Fog.Delta (FogDelta, diff, deltaKind, netChange, DeltaKind(..))

-- | Given a list of (before, after) pairs, return deltas flagged as arbitrage.
detectArbitrage :: [(FogMap, FogMap)] -> [FogDelta]
detectArbitrage = filter isArbitrage . map (uncurry diff)
  where
    isArbitrage d = deltaKind d == Arbitrage

-- | Net change in total system ignorance across all agents.
-- Negative = fog lifted. Zero = arbitrage. Positive = deepening.
systemFogChange :: [(FogMap, FogMap)] -> Int
systemFogChange = sum . map (netChange . uncurry diff)
