-- | FogDelta — the change between two FogMap snapshots.
--
-- diff is a pure function. Two values in, one value out.
-- The result tells you whether ignorance shrank, grew, or just moved.
module Fog.Delta
  ( FogDelta(..)
  , DeltaKind(..)
  , diff
  , deltaKind
  , netChange
  , entropyDelta
  , summarise
  ) where

import Data.Map.Strict (Map)
import qualified Data.Map.Strict as Map
import Data.Set (Set)
import qualified Data.Set as Set
import Fog.Gap (effectiveConfidence)
import Fog.Map (FogMap(..), fogKeys, fogAgentId, fogVolume, fogEntropy)

-- | What kind of change happened.
data DeltaKind
  = Static      -- ^ Nothing changed.
  | Lift        -- ^ Fog shrank — new signal entered.
  | Arbitrage   -- ^ Fog moved but didn't shrink — ignorance redistributed.
  | Deepening   -- ^ Fog grew — agent knows less than before.
  deriving (Eq, Show)

-- | The change between two fog map snapshots.
-- Stores map references for weighted computations.
data FogDelta = FogDelta
  { deltaAgentId    :: String
  , gapsLifted      :: Set String     -- ^ Present in before, absent in after.
  , gapsAdded       :: Set String     -- ^ Absent in before, present in after.
  , gapsUnchanged   :: Set String     -- ^ Present in both.
  , deltaBeforeMap  :: FogMap
  , deltaAfterMap   :: FogMap
  , deltaNow        :: Double         -- ^ POSIX time snapshot.
  , deltaHalfLife   :: Double
  } deriving (Eq, Show)

eps :: Double
eps = 1.0e-9

-- | Diff two fog maps. Pure function.
-- Pass current POSIX time and half-life for weighted net and entropy.
diff :: Double -> Double -> FogMap -> FogMap -> FogDelta
diff now hl before after = FogDelta
  { deltaAgentId   = fogAgentId before
  , gapsLifted     = Set.difference bk ak
  , gapsAdded      = Set.difference ak bk
  , gapsUnchanged  = Set.intersection bk ak
  , deltaBeforeMap = before
  , deltaAfterMap  = after
  , deltaNow       = now
  , deltaHalfLife  = hl
  }
  where
    bk = fogKeys before
    ak = fogKeys after

-- | Weighted net change in fog volume.
--
-- @
-- net = vol(added) − vol(lifted)
-- @
--
-- Uses effective_confidence as weights. Negative is good.
netChange :: FogDelta -> Double
netChange d =
  let now  = deltaNow d
      hl   = deltaHalfLife d
      eff fmap k = maybe 0.0 (effectiveConfidence now hl)
                        (Map.lookup k (fogGaps fmap))
      volAdded  = sum [ eff (deltaAfterMap  d) k | k <- Set.toList (gapsAdded  d) ]
      volLifted = sum [ eff (deltaBeforeMap d) k | k <- Set.toList (gapsLifted d) ]
  in volAdded - volLifted

-- | Change in fog entropy between before and after.
--
-- @
-- ΔH = H(after) − H(before)
-- @
--
-- ΔH < 0: fog became more concentrated — fewer, better-defined gaps.
-- ΔH > 0: fog spread out — broader, more diffuse uncertainty.
-- ΔH ≈ 0: same structural shape (even if individual gaps changed).
entropyDelta :: FogDelta -> Double
entropyDelta d =
  let now = deltaNow d
      hl  = deltaHalfLife d
  in fogEntropy now hl (deltaAfterMap d) - fogEntropy now hl (deltaBeforeMap d)

-- | Classify the delta.
deltaKind :: FogDelta -> DeltaKind
deltaKind d
  | abs n < eps, Set.null (gapsLifted d) = Static
  | n < 0                                = Lift
  | abs n < eps                          = Arbitrage
  | otherwise                            = Deepening
  where n = netChange d

fmt3 :: Double -> String
fmt3 x = show (fromIntegral (round (x * 1000) :: Int) / 1000.0 :: Double)

-- | Human-readable summary.
summarise :: FogDelta -> String
summarise d =
  let n  = netChange d
      ed = entropyDelta d
      edStr = " ΔH=" <> (if ed >= 0 then "+" else "") <> fmt3 ed
  in case deltaKind d of
    Static    ->
      "[" <> deltaAgentId d <> "] static — no change" <> edStr
    Lift      ->
      "[" <> deltaAgentId d <> "] lift — net=" <> fmt3 n <> " (fog clearing)" <> edStr
    Arbitrage ->
      "[" <> deltaAgentId d <> "] arbitrage — "
      <> "+" <> show (Set.size (gapsAdded  d))
      <> " -" <> show (Set.size (gapsLifted d))
      <> " net=" <> fmt3 n
      <> " (ignorance redistributed, not reduced)" <> edStr
    Deepening ->
      "[" <> deltaAgentId d <> "] deepening — net=+" <> fmt3 n <> edStr
