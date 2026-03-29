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
  , summarise
  ) where

import Data.Set (Set)
import qualified Data.Set as Set
import Fog.Map (FogMap, fogKeys, fogAgentId)

-- | What kind of change happened.
data DeltaKind
  = Static      -- ^ Nothing changed.
  | Lift        -- ^ Fog shrank — new signal entered.
  | Arbitrage   -- ^ Fog moved but didn't shrink — ignorance redistributed.
  | Deepening   -- ^ Fog grew — agent knows less than before.
  deriving (Eq, Show)

-- | The change between two fog map snapshots.
data FogDelta = FogDelta
  { deltaAgentId    :: String
  , gapsLifted      :: Set String   -- ^ Present in before, absent in after.
  , gapsAdded       :: Set String   -- ^ Absent in before, present in after.
  , gapsUnchanged   :: Set String   -- ^ Present in both.
  } deriving (Eq, Show)

-- | Diff two fog maps. Pure function.
diff :: FogMap -> FogMap -> FogDelta
diff before after = FogDelta
  { deltaAgentId  = fogAgentId before
  , gapsLifted    = Set.difference bk ak
  , gapsAdded     = Set.difference ak bk
  , gapsUnchanged = Set.intersection bk ak
  }
  where
    bk = fogKeys before
    ak = fogKeys after

-- | Net change in fog. Negative is good.
netChange :: FogDelta -> Int
netChange d = Set.size (gapsAdded d) - Set.size (gapsLifted d)

-- | Classify the delta.
deltaKind :: FogDelta -> DeltaKind
deltaKind d
  | net == 0, Set.null (gapsLifted d) = Static
  | net <  0                          = Lift
  | net == 0                          = Arbitrage
  | otherwise                         = Deepening
  where net = netChange d

-- | Human-readable summary.
summarise :: FogDelta -> String
summarise d = case deltaKind d of
  Static    -> "[" <> deltaAgentId d <> "] static — no change"
  Lift      -> "[" <> deltaAgentId d <> "] lift — net=" <> show (netChange d) <> " (fog clearing)"
  Arbitrage -> "[" <> deltaAgentId d <> "] arbitrage — "
            <> "+" <> show (Set.size (gapsAdded   d))
            <> " -" <> show (Set.size (gapsLifted d))
            <> " net=0 (ignorance redistributed, not reduced)"
  Deepening -> "[" <> deltaAgentId d <> "] deepening — net=+"
            <> show (netChange d)
