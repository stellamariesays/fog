-- | FogSeam — boundary between two agents' fog maps.
--
-- measure is a pure function. Two maps in, one seam out.
-- tension tells you whether the ignorance is asymmetric (transfer potential)
-- or symmetric (pure arbitrage territory).
module Fog.Seam
  ( FogSeam(..)
  , SeamInterpretation(..)
  , measure
  , tension
  , systemGaps
  , interpret
  , summarise
  ) where

import Data.Set (Set)
import qualified Data.Set as Set
import Fog.Map (FogMap, fogKeys, fogAgentId)

-- | What the seam is telling you.
data SeamInterpretation
  = HighPotential  -- ^ Asymmetric blind spots — strong transfer signal.
  | ActiveSeam     -- ^ Partial overlap — exchange probable.
  | LowTension     -- ^ Mostly shared fog — limited exchange value.
  | FlatSeam       -- ^ Identical fog — no transfer possible.
  deriving (Eq, Show)

-- | Boundary between two agents' fog states.
data FogSeam = FogSeam
  { seamAgentA  :: String
  , seamAgentB  :: String
  , onlyInA     :: Set String  -- ^ A dark, B may have signal.
  , onlyInB     :: Set String  -- ^ B dark, A may have signal.
  , seamShared  :: Set String  -- ^ Both dark — needs external signal.
  } deriving (Eq, Show)

-- | Measure the seam between two agents' fog maps. Pure function.
measure :: FogMap -> FogMap -> FogSeam
measure mapA mapB = FogSeam
  { seamAgentA = fogAgentId mapA
  , seamAgentB = fogAgentId mapB
  , onlyInA    = Set.difference ak bk
  , onlyInB    = Set.difference bk ak
  , seamShared = Set.intersection ak bk
  }
  where
    ak = fogKeys mapA
    bk = fogKeys mapB

-- | Seam tension: fraction of gaps that are asymmetric.
-- High tension → different blind spots → transfer potential.
tension :: FogSeam -> Double
tension s
  | total == 0 = 0.0
  | otherwise  = fromIntegral asymmetric / fromIntegral total
  where
    asymmetric = Set.size (onlyInA s) + Set.size (onlyInB s)
    total      = asymmetric + Set.size (seamShared s)

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

-- | Human-readable interpretation.
interpretLabel :: SeamInterpretation -> String
interpretLabel HighPotential = "high-potential seam — asymmetric blind spots, strong transfer signal"
interpretLabel ActiveSeam    = "active seam — partial overlap, exchange probable"
interpretLabel LowTension    = "low-tension seam — mostly shared fog, limited exchange value"
interpretLabel FlatSeam      = "flat seam — identical fog, no transfer possible"

-- | Human-readable summary.
summarise :: FogSeam -> String
summarise s =
  "FogSeam(" <> seamAgentA s <> "↔" <> seamAgentB s <> ") "
  <> "tension=" <> show (round2 (tension s)) <> " "
  <> "A-only=" <> show (Set.size (onlyInA s)) <> " "
  <> "B-only=" <> show (Set.size (onlyInB s)) <> " "
  <> "shared=" <> show (Set.size (seamShared s)) <> " "
  <> "— " <> interpretLabel (interpret s)
  where
    round2 x = fromIntegral (round (x * 100) :: Int) / 100.0 :: Double
