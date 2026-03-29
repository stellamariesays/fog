-- | Detect epistemic arbitrage across a mesh of agents.
--
-- Arbitrage: ignorance is moving but not shrinking.
-- The system looks more informed. The total dark is conserved.
module Fog.Detect.Arbitrage
  ( detectArbitrage
  , systemFogChange
  , systemEntropyChange
  , isDarkConserved
  ) where

import Fog.Map (FogMap)
import Fog.Delta (FogDelta, diff, deltaKind, netChange, entropyDelta, DeltaKind(..))

eps :: Double
eps = 1.0e-9

-- | Given a list of (before, after) pairs, return deltas flagged as arbitrage.
-- Uses weighted net (effective_confidence), not raw counts.
detectArbitrage :: Double -> Double -> [(FogMap, FogMap)] -> [FogDelta]
detectArbitrage now hl = filter isArbitrage . map (uncurry (diff now hl))
  where
    isArbitrage d = deltaKind d == Arbitrage

-- | Weighted net change in total system ignorance across all agents.
-- Negative = fog lifted. Zero = redistribution. Positive = deepening.
systemFogChange :: Double -> Double -> [(FogMap, FogMap)] -> Double
systemFogChange now hl = sum . map (netChange . uncurry (diff now hl))

-- | Net change in total system entropy across all agents.
-- Negative = structure became more concentrated.
-- Zero     = same entropy shape.
-- Positive = broader, more diffuse uncertainty.
systemEntropyChange :: Double -> Double -> [(FogMap, FogMap)] -> Double
systemEntropyChange now hl = sum . map (entropyDelta . uncurry (diff now hl))

-- | True if total system fog volume is conserved despite individual churn.
isDarkConserved :: Double -> Double -> [(FogMap, FogMap)] -> Bool
isDarkConserved now hl pairs = abs (systemFogChange now hl pairs) < eps
