-- | A single gap in an agent's knowledge.
module Fog.Gap
  ( GapKind(..)
  , Gap(..)
  , newGap
  ) where

import Data.Map.Strict (Map)
import qualified Data.Map.Strict as Map

-- | Why the gap exists.
data GapKind
  = KnownUnknown    -- ^ The agent knows it doesn't know this.
  | InferredUnknown -- ^ Inferred from mesh topology or seam structure.
  | Stale           -- ^ Once known, now uncertain.
  deriving (Eq, Ord, Show)

-- | A gap in an agent's knowledge map.
data Gap = Gap
  { gapKey        :: String
  , gapKind       :: GapKind
  , gapDomain     :: Maybe String
  , gapConfidence :: Double
  , gapMetadata   :: Map String String
  } deriving (Eq, Show)

-- | Construct a gap with defaults.
newGap :: String -> GapKind -> Maybe String -> Gap
newGap key kind domain = Gap
  { gapKey        = key
  , gapKind       = kind
  , gapDomain     = domain
  , gapConfidence = 1.0
  , gapMetadata   = Map.empty
  }
