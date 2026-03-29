-- | FogSeam — boundary between two agents' fog maps.
--
-- measure is a pure function. Two maps in, one seam out.
-- tension tells you whether the ignorance is asymmetric (transfer potential)
-- or symmetric (pure arbitrage territory).
--
-- KL and JS divergence measure the structural distance between fog distributions.
module Fog.Seam
  ( FogSeam(..)
  , SeamInterpretation(..)
  , measure
  , tension
  , klDivergence
  , jsDivergence
  , systemGaps
  , interpret
  , summarise
  ) where

import Data.Map.Strict (Map)
import qualified Data.Map.Strict as Map
import Data.Set (Set)
import qualified Data.Set as Set
import Fog.Gap (Gap, effectiveConfidence, defaultHalfLife)
import Fog.Map (FogMap(..), fogKeys, fogAgentId, fogVolume)

-- | What the seam is telling you.
data SeamInterpretation
  = HighPotential  -- ^ Asymmetric blind spots — strong transfer signal.
  | ActiveSeam     -- ^ Partial overlap — exchange probable.
  | LowTension     -- ^ Mostly shared fog — limited exchange value.
  | FlatSeam       -- ^ Identical fog — no transfer possible.
  deriving (Eq, Show)

-- | Boundary between two agents' fog states.
-- Stores map references for weighted computations.
data FogSeam = FogSeam
  { seamAgentA  :: String
  , seamAgentB  :: String
  , onlyInA     :: Set String   -- ^ A dark, B may have signal.
  , onlyInB     :: Set String   -- ^ B dark, A may have signal.
  , seamShared  :: Set String   -- ^ Both dark — needs external signal.
  , seamMapA    :: FogMap
  , seamMapB    :: FogMap
  , seamNow     :: Double       -- ^ POSIX time snapshot used for decay.
  , seamHalfLife :: Double
  } deriving (Eq, Show)

smooth :: Double
smooth = 1.0e-9  -- ε for KL where a gap is absent in one distribution

-- | Measure the seam between two agents' fog maps.
-- Pass current POSIX time and half-life for weighted computations.
measure :: Double -> Double -> FogMap -> FogMap -> FogSeam
measure now hl mapA mapB = FogSeam
  { seamAgentA   = fogAgentId mapA
  , seamAgentB   = fogAgentId mapB
  , onlyInA      = Set.difference ak bk
  , onlyInB      = Set.difference bk ak
  , seamShared   = Set.intersection ak bk
  , seamMapA     = mapA
  , seamMapB     = mapB
  , seamNow      = now
  , seamHalfLife = hl
  }
  where
    ak = fogKeys mapA
    bk = fogKeys mapB

-- | Weighted seam tension: fraction of total fog volume that is asymmetric.
--
-- @
-- tension = vol(A-only ∪ B-only) / vol(A ∪ B)
-- @
--
-- 1.0 = perfectly asymmetric (maximum transfer potential)
-- 0.0 = identical fog (pure arbitrage territory)
tension :: FogSeam -> Double
tension s
  | total <= 0 = 0.0
  | otherwise  = volAsym / total
  where
    now  = seamNow s
    hl   = seamHalfLife s
    eff  fmap k = maybe 0.0 (effectiveConfidence now hl)
                        (Map.lookup k (fogGaps fmap))

    volA     = sum [ eff (seamMapA s) k | k <- Set.toList (onlyInA s) ]
    volB     = sum [ eff (seamMapB s) k | k <- Set.toList (onlyInB s) ]
    volAsym  = volA + volB
    volShared = sum [ max (eff (seamMapA s) k) (eff (seamMapB s) k)
                    | k <- Set.toList (seamShared s) ]
    total    = volAsym + volShared

-- | KL divergence between the two fog distributions.
--
-- @
-- D_KL(A ∥ B) = Σ p_A(x) log(p_A(x) \/ p_B(x))
-- @
--
-- @direction = True@: A→B. @direction = False@: B→A.
-- Asymmetric — A→B ≠ B→A. Absent gaps are smoothed with ε = 1e-9.
klDivergence
  :: Bool      -- ^ True = A→B, False = B→A
  -> FogSeam
  -> Double
klDivergence aToB s =
  let now  = seamNow s
      hl   = seamHalfLife s
      va   = max (fogVolume now hl (seamMapA s)) 1.0e-9
      vb   = max (fogVolume now hl (seamMapB s)) 1.0e-9
      universe = Set.union (fogKeys (seamMapA s)) (fogKeys (seamMapB s))

      pa k = maybe smooth (\g -> effectiveConfidence now hl g / va)
                   (Map.lookup k (fogGaps (seamMapA s)))
      pb k = maybe smooth (\g -> effectiveConfidence now hl g / vb)
                   (Map.lookup k (fogGaps (seamMapB s)))

      term k = let (p, q) = if aToB then (pa k, pb k) else (pb k, pa k)
               in p * log (p / q)
  in sum [ term k | k <- Set.toList universe ]

-- | Jensen-Shannon divergence — symmetric, bounded [0,1] in bits.
--
-- @
-- JS(A, B) = ½ D_KL(A ∥ M) + ½ D_KL(B ∥ M)   where M = (A + B) \/ 2
-- @
--
-- 0.0 = identical distributions. 1.0 = completely disjoint fog.
jsDivergence :: FogSeam -> Double
jsDivergence s =
  let now      = seamNow s
      hl       = seamHalfLife s
      va       = max (fogVolume now hl (seamMapA s)) 1.0e-9
      vb       = max (fogVolume now hl (seamMapB s)) 1.0e-9
      universe = Set.union (fogKeys (seamMapA s)) (fogKeys (seamMapB s))

      pa k = maybe smooth (\g -> effectiveConfidence now hl g / va)
                   (Map.lookup k (fogGaps (seamMapA s)))
      pb k = maybe smooth (\g -> effectiveConfidence now hl g / vb)
                   (Map.lookup k (fogGaps (seamMapB s)))

      kl2 p q = if p > 0 then p * logBase 2 (p / q) else 0.0
      term k  = let p = pa k; q = pb k; m = (p + q) / 2
                in 0.5 * kl2 p m + 0.5 * kl2 q m
  in sum [ term k | k <- Set.toList universe ]

-- | Gaps that need external signal — neither agent can fill from the other.
systemGaps :: FogSeam -> Set String
systemGaps = seamShared

-- | Classify the seam.
interpret :: FogSeam -> SeamInterpretation
interpret s
  | t > 0.7   = HighPotential
  | t > 0.4   = ActiveSeam
  | t > 0.0   = LowTension
  | otherwise = FlatSeam
  where t = tension s

interpretLabel :: SeamInterpretation -> String
interpretLabel HighPotential = "high-potential — asymmetric blind spots, strong transfer signal"
interpretLabel ActiveSeam    = "active — partial overlap, exchange probable"
interpretLabel LowTension    = "low-tension — mostly shared fog, limited exchange value"
interpretLabel FlatSeam      = "flat — identical fog, no transfer possible"

fmt2 :: Double -> String
fmt2 x = show (fromIntegral (round (x * 1000) :: Int) / 1000.0 :: Double)

-- | Human-readable summary.
summarise :: FogSeam -> String
summarise s =
  "FogSeam(" <> seamAgentA s <> "↔" <> seamAgentB s <> ") "
  <> "tension=" <> fmt2 (tension s) <> " "
  <> "A-only=" <> show (Set.size (onlyInA s)) <> " "
  <> "B-only=" <> show (Set.size (onlyInB s)) <> " "
  <> "shared=" <> show (Set.size (seamShared s)) <> " "
  <> "KL(A→B)=" <> fmt2 (klDivergence True s) <> " "
  <> "JS=" <> fmt2 (jsDivergence s) <> " "
  <> "— " <> interpretLabel (interpret s)
