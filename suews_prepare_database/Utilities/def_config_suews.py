from typing import Dict, List, Optional, Union, Literal, Tuple, Type, Generic, TypeVar
from pydantic import (
    BaseModel,
    Field,
    model_validator,
    field_validator,
    PrivateAttr,
    conlist,
)
import numpy as np
from enum import Enum
import pandas as pd
import scipy as sp
import yaml
import pdb
import math

T = TypeVar('T')

class Reference(BaseModel):
    desc: Optional[str] = None
    ID: Optional[str] = None
    DOI: Optional[str] = None


class ValueWithDOI(BaseModel, Generic[T]):
    value: T
    ref: Optional[Reference] = None

    def __init__(self, value: T, ref: Optional[Reference] = None):
        if isinstance(value, (np.float64, np.float32)):
            value = float(value)
        elif isinstance(value, (np.int64, np.int32)):
            value = int(value)
        super().__init__(value=value, ref=ref)

    def __str__(self):
        return f"{self.value}"

    def __repr__(self):
        return f"{self.value}"
    
    def __eq__(self, other):
        if isinstance(other, ValueWithDOI):
            return self.value == other.value
        return self.value == other

    def __lt__(self, other):
        if isinstance(other, ValueWithDOI):
            return self.value < other.value
        return self.value < other

    def __le__(self, other):
        if isinstance(other, ValueWithDOI):
            return self.value <= other.value
        return self.value <= other

    def __gt__(self, other):
        if isinstance(other, ValueWithDOI):
            return self.value > other.value
        return self.value > other

    def __ge__(self, other):
        if isinstance(other, ValueWithDOI):
            return self.value >= other.value
        return self.value >= other

    def __ne__(self, other):
        if isinstance(other, ValueWithDOI):
            return self.value != other.value
        return self.value != other

def init_df_state(grid_id: int) -> pd.DataFrame:
    idx = pd.Index([grid_id], name="grid")
    col = pd.MultiIndex.from_tuples([("gridiv", "0")], names=["var", "ind_dim"])
    df_state = pd.DataFrame(index=idx, columns=col)
    df_state.loc[grid_id, ("gridiv", "0")] = grid_id
    return df_state


class SurfaceType(str, Enum):
    PAVED = "paved"
    BLDGS = "bldgs"
    EVETR = "evetr"
    DECTR = "dectr"
    GRASS = "grass"
    BSOIL = "bsoil"
    WATER = "water"


class SnowAlb(BaseModel):
    snowalb: ValueWithDOI[float] = Field(
        description="Snow albedo",
        default=ValueWithDOI(0.7),
        ge=0, le=1,
    )

    def to_df_state(self, grid_id: int) -> pd.DataFrame:
        """Convert snow albedo to DataFrame state format.

        Args:
            grid_id: Grid ID for the DataFrame index

        Returns:
            pd.DataFrame: DataFrame containing snow albedo parameters
        """
        df_state = init_df_state(grid_id)
        df_state[("snowalb", "0")] = self.snowalb.value
        return df_state

    @classmethod
    def from_df_state(cls, df: pd.DataFrame, grid_id: int) -> "SnowAlb":
        """
        Reconstruct SnowAlb from a DataFrame state format.

        Args:
            df (pd.DataFrame): DataFrame containing snow albedo parameters.
            grid_id (int): Grid ID for the DataFrame index.

        Returns:
            SnowAlb: Instance of SnowAlb.
        """
        snowalb = df.loc[grid_id, ("snowalb", "0")]
        return cls(snowalb=ValueWithDOI(snowalb))


class WaterUse(BaseModel):
    wu_total: ValueWithDOI[float] = Field(
        description="Total water use",
        default=ValueWithDOI(value=0.0),
        ge=0,
    )  # Default set to 0.0 means no irrigation.
    wu_auto: ValueWithDOI[float] = Field(
        description="Automatic water use",
        default=ValueWithDOI(value=0.0),
        ge=0,
    )
    wu_manual: ValueWithDOI[float] = Field(
        description="Manual water use",
        default=ValueWithDOI(value=0.0),
        ge=0,
    )

    ref: Optional[Reference] = None

    def to_df_state(self, veg_idx: int, grid_id: int) -> pd.DataFrame:
        """Convert water use to DataFrame state format."""
        df_state = init_df_state(grid_id)
        df_state.loc[grid_id, ("wuday_id", f"({veg_idx * 3 + 0},)")] = self.wu_total.value
        df_state.loc[grid_id, ("wuday_id", f"({veg_idx * 3 + 1},)")] = self.wu_auto.value
        df_state.loc[grid_id, ("wuday_id", f"({veg_idx * 3 + 2},)")] = self.wu_manual.value
        return df_state

    @classmethod
    def from_df_state(cls, df: pd.DataFrame, veg_idx: int, grid_id: int) -> "WaterUse":
        """
        Reconstruct WaterUse from a DataFrame state format.

        Args:
            df (pd.DataFrame): DataFrame containing water use parameters.
            veg_idx (int): Vegetation index for identifying columns.
            grid_id (int): Grid ID for the DataFrame index.

        Returns:
            WaterUse: Instance of WaterUse.
        """
        wu_total = df.loc[grid_id, ("wuday_id", f"({veg_idx * 3 + 0},)")].item()
        wu_auto = df.loc[grid_id, ("wuday_id", f"({veg_idx * 3 + 1},)")].item()
        wu_manual = df.loc[grid_id, ("wuday_id", f"({veg_idx * 3 + 2},)")].item()

        return cls(
            wu_total=ValueWithDOI[float](wu_total),
            wu_auto=ValueWithDOI[float](wu_auto),
            wu_manual=ValueWithDOI[float](wu_manual)
        )


class SurfaceInitialState(BaseModel):
    """Base initial state parameters for all surface types"""

    state: ValueWithDOI[float] = Field(
        description="Initial state of the surface",
        default=ValueWithDOI(0.0),
        ge=0,
    )  # Default set to 0.0 means dry surface.
    soilstore: ValueWithDOI[float] = Field(
        description="Initial soil store (essential for QE)",
        default=ValueWithDOI(150.0),
        ge=10,
    )  # Default set to 150.0 (wet soil) and ge=10 (less than 10 would be too dry) are physically reasonable for a model run.
    snowfrac: Optional[Union[ValueWithDOI[float], None]] = Field(
        description="Snow fraction",
        default=ValueWithDOI(0.0),
        ge=0, le=1,
    )  # Default set to 0.0 means no snow on the ground.
    snowpack: Optional[Union[ValueWithDOI[float], None]] = Field(
        description="Snow pack",
        default=ValueWithDOI(0.0),
        ge=0,
    )
    icefrac: Optional[Union[ValueWithDOI[float], None]] = Field(
        description="Ice fraction",
        default=ValueWithDOI(0.0),
        ge=0, le=1,
    )
    snowwater: Optional[Union[ValueWithDOI[float], None]] = Field(
        description="Snow water",
        default=ValueWithDOI(0.0),
        ge=0,
    )
    snowdens: Optional[Union[ValueWithDOI[float], None]] = Field(
        description="Snow density",
        default=ValueWithDOI(0.0),
        ge=0,
    )
    temperature: ValueWithDOI[List[float]] = Field(
        description="Initial temperature for each thermal layer",
        default=ValueWithDOI([15.0, 15.0, 15.0, 15.0, 15.0]),
    )  # We need to check/undestand what model are these temperatures related to. ESTM? What surface type (wall and roof) of building?
    tsfc: Optional[Union[ValueWithDOI[float], None]] = Field(
        description="Initial exterior surface temperature",
        default=ValueWithDOI(15.0),
    )
    tin: Optional[Union[ValueWithDOI[float], None]] = Field(
        description="Initial interior surface temperature",
        default=ValueWithDOI(20.0)
    )  # We need to know which model is using this.
    _surface_type: Optional[SurfaceType] = PrivateAttr(default=None)

    ref: Optional[Reference] = None

    @field_validator("temperature", mode="before")
    def validate_temperature(cls, v):
        if isinstance(v, dict):
            value = v['value']
        else:
            value = v.value
        if len(value) != 5:
            raise ValueError("temperature must have exactly 5 items")
        return v

    def set_surface_type(self, surface_type: SurfaceType):
        """Set surface type"""
        self._surface_type = surface_type

    def get_surface_index(self) -> int:
        """Get surface index"""
        return {
            SurfaceType.PAVED: 0,
            SurfaceType.BLDGS: 1,
            SurfaceType.EVETR: 2,
            SurfaceType.DECTR: 3,
            SurfaceType.GRASS: 4,
            SurfaceType.BSOIL: 5,
            SurfaceType.WATER: 6,
        }[self._surface_type]

    def to_df_state(
        self, grid_id: int, vert_idx: int = None, is_roof: bool = False
    ) -> pd.DataFrame:
        """Convert base surface initial state to DataFrame state format.

        Args:
            grid_id: Grid ID for the DataFrame index

        Returns:
            pd.DataFrame: DataFrame containing initial state parameters
        """
        df_state = init_df_state(grid_id)

        # Get surface index
        if vert_idx is None:
            idx = self.get_surface_index()
            str_type = "surf"
        else:
            idx = vert_idx
            str_type = "roof" if is_roof else "wall"
        # Set basic state parameters
        df_state[(f"state_{str_type}", f"({idx},)")] = self.state.value
        df_state[(f"soilstore_{str_type}", f"({idx},)")] = self.soilstore.value

        # Set snow/ice parameters if present
        if self.snowfrac is not None:
            df_state[(f"snowfrac", f"({idx},)")] = self.snowfrac.value
        if self.snowpack is not None:
            df_state[(f"snowpack", f"({idx},)")] = self.snowpack.value
        if self.icefrac is not None:
            df_state[(f"icefrac", f"({idx},)")] = self.icefrac.value
        if self.snowwater is not None:
            df_state[(f"snowwater", f"({idx},)")] = self.snowwater.value
        if self.snowdens is not None:
            df_state[(f"snowdens", f"({idx},)")] = self.snowdens.value

        # Set temperature parameters
        for i, temp in enumerate(self.temperature.value):
            df_state[(f"temp_{str_type}", f"({idx}, {i})")] = temp

        if self.tsfc is not None:
            df_state[(f"tsfc_{str_type}", f"({idx},)")] = self.tsfc.value
        if self.tin is not None:
            df_state[(f"tin_{str_type}", f"({idx},)")] = self.tin.value

        return df_state

    @classmethod
    def from_df_state(
        cls, df: pd.DataFrame, grid_id: int, surf_idx: int, str_type: str = "surf"
    ) -> "SurfaceInitialState":
        """
        Reconstruct SurfaceInitialState from a DataFrame state format.

        Args:
            df (pd.DataFrame): DataFrame containing surface state parameters.
            grid_id (int): Grid ID for the DataFrame index.
            surf_idx (int): Surface index for identifying columns.
            str_type (str): Surface type prefix ("surf", "roof", or "wall").

        Returns:
            SurfaceInitialState: Instance of SurfaceInitialState.
        """
        # Base surface state parameters
        state = ValueWithDOI[float](df.loc[grid_id, (f"state_{str_type}", f"({surf_idx},)")])
        soilstore = ValueWithDOI[float](df.loc[grid_id, (f"soilstore_{str_type}", f"({surf_idx},)")])

        # Snow/ice parameters
        if str_type not in ["roof", "wall"]:
            snowfrac = ValueWithDOI[float](df.loc[grid_id, (f"snowfrac", f"({surf_idx},)")])
            snowpack = ValueWithDOI[float](df.loc[grid_id, (f"snowpack", f"({surf_idx},)")])
            icefrac = ValueWithDOI[float](df.loc[grid_id, (f"icefrac", f"({surf_idx},)")])
            snowwater = ValueWithDOI[float](df.loc[grid_id, (f"snowwater", f"({surf_idx},)")])
            snowdens = ValueWithDOI[float](df.loc[grid_id, (f"snowdens", f"({surf_idx},)")])
        else:
            snowfrac = None
            snowpack = None
            icefrac = None
            snowwater = None
            snowdens = None

        # Temperature parameters
        temperature = ValueWithDOI[List[float]]([
            df.loc[grid_id, (f"temp_{str_type}", f"({surf_idx}, {i})")]
            for i in range(5)
        ])

        # Exterior and interior surface temperature
        tsfc = ValueWithDOI[float](df.loc[grid_id, (f"tsfc_{str_type}", f"({surf_idx},)")])
        tin = ValueWithDOI[float](df.loc[grid_id, (f"tin_{str_type}", f"({surf_idx},)")])

        return cls(
            state=state,
            soilstore=soilstore,
            snowfrac=snowfrac,
            snowpack=snowpack,
            icefrac=icefrac,
            snowwater=snowwater,
            snowdens=snowdens,
            temperature=temperature,
            tsfc=tsfc,
            tin=tin,
        )


class InitialStatePaved(SurfaceInitialState):
    _surface_type: Literal[SurfaceType.PAVED] = SurfaceType.PAVED


class InitialStateBldgs(SurfaceInitialState):
    _surface_type: Literal[SurfaceType.BLDGS] = SurfaceType.BLDGS


class InitialStateVeg(SurfaceInitialState):
    """Base initial state parameters for vegetated surfaces"""

    alb_id: ValueWithDOI[float] = Field(
        description="Initial albedo for vegetated surfaces (depends on time of year).",
        default=ValueWithDOI(0.25),
    )
    lai_id: ValueWithDOI[float] = Field(
        description="Initial leaf area index (depends on time of year).",
        default=ValueWithDOI(1.0)
    )
    gdd_id: ValueWithDOI[float] = Field(
        description="Growing degree days  on day 1 of model run ID",
        default=ValueWithDOI(0)
    )  # We need to check this and give info for setting values.
    sdd_id: ValueWithDOI[float] = Field(
        description="Senescence degree days ID",
        default=ValueWithDOI(0)
    )  # This need to be consistent with GDD.
    wu: WaterUse = Field(default_factory=WaterUse)

    ref: Optional[Reference] = None

    @model_validator(mode="after")
    def validate_surface_state(self) -> "InitialStateVeg":
        """Validate state based on surface type"""
        # Skip validation if surface type not yet set
        if not hasattr(self, "_surface_type") or self._surface_type is None:
            return self

        if self._surface_type not in [
            SurfaceType.DECTR,
            SurfaceType.EVETR,
            SurfaceType.GRASS,
        ]:
            raise ValueError(
                f"Invalid surface type {self._surface_type} for vegetated surface"
            )
        return self

    def to_df_state(self, grid_id: int) -> pd.DataFrame:
        """Convert vegetated surface initial state to DataFrame state format.

        Args:
            grid_id: Grid ID for the DataFrame index

        Returns:
            pd.DataFrame: DataFrame containing initial state parameters
        """
        # Get base surface state parameters
        df_state = super().to_df_state(grid_id)

        # Get surface index
        surf_idx = self.get_surface_index()
        veg_idx = surf_idx - 2

        # Add vegetated surface specific parameters
        # alb is universal so use surf_idx
        df_state[("alb", f"({surf_idx},)")] = self.alb_id.value
        # others are aligned with veg_idx
        df_state[("lai_id", f"({veg_idx},)")] = self.lai_id.value
        df_state[("gdd_id", f"({veg_idx},)")] = self.gdd_id.value
        df_state[("sdd_id", f"({veg_idx},)")] = self.sdd_id.value

        # Add water use parameters
        df_wu = self.wu.to_df_state(veg_idx, grid_id)
        df_state = pd.concat([df_state, df_wu], axis=1)

        # Drop any duplicate columns
        df_state = df_state.loc[:, ~df_state.columns.duplicated()]

        return df_state

    @classmethod
    def from_df_state(
        cls, df: pd.DataFrame, grid_id: int, surf_idx: int
    ) -> "InitialStateVeg":
        """
        Reconstruct VegetatedSurfaceInitialState from a DataFrame state format."""
        base_instance = SurfaceInitialState.from_df_state(df, grid_id, surf_idx)

        # Vegetated surface-specific parameters
        alb_key = ("alb", f"({surf_idx},)")
        lai_key = ("lai_id", f"({surf_idx - 2},)")
        gdd_key = ("gdd_id", f"({surf_idx - 2},)")
        sdd_key = ("sdd_id", f"({surf_idx - 2},)")

        alb_id = df.loc[grid_id, alb_key]
        lai_id = df.loc[grid_id, lai_key]
        gdd_id = df.loc[grid_id, gdd_key]
        sdd_id = df.loc[grid_id, sdd_key]

        # Convert to ValueWithDOI
        alb_id = ValueWithDOI[float](alb_id)
        lai_id = ValueWithDOI[float](lai_id)
        gdd_id = ValueWithDOI[float](gdd_id)
        sdd_id = ValueWithDOI[float](sdd_id)

        # Reconstruct WaterUse instance
        veg_idx = surf_idx - 2
        wu = WaterUse.from_df_state(df, veg_idx, grid_id)

        return cls(
            **base_instance.model_dump(),
            alb_id=alb_id,
            lai_id=lai_id,
            gdd_id=gdd_id,
            sdd_id=sdd_id,
            wu=wu,
        )


class InitialStateEvetr(InitialStateVeg):
    _surface_type: Literal[SurfaceType.EVETR] = SurfaceType.EVETR

    def to_df_state(self, grid_id: int) -> pd.DataFrame:
        """Convert evergreen tree initial state to DataFrame state format."""
        df_state = super().to_df_state(grid_id)
        df_state[("albevetr_id", "0")] = self.alb_id.value
        return df_state

    @classmethod
    def from_df_state(
        cls, df: pd.DataFrame, grid_id: int, surf_idx: int
    ) -> "InitialStateEvetr":
        """
        Reconstruct InitialStateEvetr from a DataFrame state format.

        Args:
            df (pd.DataFrame): DataFrame containing EVETR state parameters.
            grid_id (int): Grid ID for the DataFrame index.
            surf_idx (int): Surface index for identifying columns.

        Returns:
            InitialStateEvetr: Instance of InitialStateEvetr.
        """
        # Call the parent class to extract common fields
        base_instance = super().from_df_state(df, grid_id, surf_idx)

        # Extract the EVETR-specific field
        alb_id = df.loc[grid_id, ("albevetr_id", "0")].item()

        # Use `base_instance.dict()` to pass the existing attributes, excluding `alb_id` to avoid duplication
        base_instance_dict = base_instance.model_dump()
        base_instance_dict["alb_id"] = {"value": alb_id}  # Update alb_id explicitly

        # Return a new instance with the updated dictionary
        return cls(**base_instance_dict)


class InitialStateDectr(InitialStateVeg):
    """Initial state parameters for deciduous trees"""

    porosity_id: ValueWithDOI[float] = Field(
        default=ValueWithDOI(0.2), description="Initial porosity for deciduous trees"
    )
    decidcap_id: ValueWithDOI[float] = Field(
        default=ValueWithDOI(0.3), description="Initial deciduous capacity for deciduous trees"
    )
    _surface_type: Literal[SurfaceType.DECTR] = SurfaceType.DECTR

    ref: Optional[Reference] = None

    @model_validator(mode="after")
    def validate_surface_state(self) -> "InitialStateDectr":
        """Validate state based on surface type"""
        # Skip validation if surface type not yet set
        if not hasattr(self, "_surface_type") or self._surface_type is None:
            return self

        if self._surface_type != SurfaceType.DECTR:
            raise ValueError("This state is only valid for deciduous trees")
        return self

    def to_df_state(self, grid_id: int) -> pd.DataFrame:
        """Convert deciduous tree initial state to DataFrame state format.

        Args:
            grid_id: Grid ID for the DataFrame index

        Returns:
            pd.DataFrame: DataFrame containing initial state parameters
        """
        # Get base vegetated surface state parameters
        df_state = super().to_df_state(grid_id)

        # Add deciduous tree specific parameters
        df_state[("porosity_id", "0")] = self.porosity_id.value
        df_state[("decidcap_id", "0")] = self.decidcap_id.value
        df_state[("albdectr_id", "0")] = self.alb_id.value

        return df_state

    @classmethod
    def from_df_state(
        cls, df: pd.DataFrame, grid_id: int, surf_idx: int
    ) -> "InitialStateDectr":
        """
        Reconstruct DeciduousTreeSurfaceInitialState from a DataFrame state format.

        Args:
            df (pd.DataFrame): DataFrame containing deciduous tree state parameters.
            grid_id (int): Grid ID for the DataFrame index.
            surf_idx (int): Surface index for identifying columns.

        Returns:
            DeciduousTreeSurfaceInitialState: Instance of DeciduousTreeSurfaceInitialState.
        """
        # Base class reconstruction
        base_instance = InitialStateVeg.from_df_state(df, grid_id, surf_idx)

        # Deciduous tree-specific parameters
        porosity_id = df.loc[grid_id, ("porosity_id", "0")]
        decidcap_id = df.loc[grid_id, ("decidcap_id", "0")]

        # Convert to ValueWithDOI
        porosity_id = ValueWithDOI[float](porosity_id)
        decidcap_id = ValueWithDOI[float](decidcap_id)

        return cls(
            **base_instance.model_dump(),
            porosity_id=porosity_id,
            decidcap_id=decidcap_id,
        )


class InitialStateGrass(InitialStateVeg):
    _surface_type: Literal[SurfaceType.GRASS] = SurfaceType.GRASS

    def to_df_state(self, grid_id: int) -> pd.DataFrame:
        """Convert grass initial state to DataFrame state format."""
        df_state = super().to_df_state(grid_id)
        df_state[("albgrass_id", "0")] = self.alb_id.value
        return df_state

    @classmethod
    def from_df_state(
        cls, df: pd.DataFrame, grid_id: int, surf_idx: int
    ) -> "InitialStateGrass":
        """
        Reconstruct InitialStateGrass from a DataFrame state format.

        Args:
            df (pd.DataFrame): DataFrame containing grass state parameters.
            grid_id (int): Grid ID for the DataFrame index.
            surf_idx (int): Surface index for identifying columns.

        Returns:
            InitialStateGrass: Instance of InitialStateGrass.
        """
        # Call the parent class to extract common fields
        base_instance = super().from_df_state(df, grid_id, surf_idx)

        # Extract the GRASS-specific field
        alb_id = df.loc[grid_id, ("albgrass_id", "0")].item()

        # Use `base_instance.dict()` to pass the existing attributes, excluding `alb_id` to avoid duplication
        base_instance_dict = base_instance.model_dump()
        base_instance_dict["alb_id"] = {"value": alb_id}  # Update alb_id explicitly

        # Return a new instance with the updated dictionary
        return cls(**base_instance_dict)


class InitialStateBsoil(SurfaceInitialState):
    _surface_type: Literal[SurfaceType.BSOIL] = SurfaceType.BSOIL


class InitialStateWater(SurfaceInitialState):
    _surface_type: Literal[SurfaceType.WATER] = SurfaceType.WATER


class InitialStates(BaseModel):
    """Initial conditions for the SUEWS model"""

    snowalb: ValueWithDOI[float] = Field(
        description="Initial snow albedo",
        default=ValueWithDOI(0.5),
        ge=0, le=1,
    )
    paved: InitialStatePaved = Field(default_factory=InitialStatePaved)
    bldgs: InitialStateBldgs = Field(default_factory=InitialStateBldgs)
    evetr: InitialStateEvetr = Field(default_factory=InitialStateEvetr)
    dectr: InitialStateDectr = Field(default_factory=InitialStateDectr)
    grass: InitialStateGrass = Field(default_factory=InitialStateGrass)
    bsoil: InitialStateBsoil = Field(default_factory=InitialStateBsoil)
    water: InitialStateWater = Field(default_factory=InitialStateWater)
    roofs: Optional[List[SurfaceInitialState]] = Field(
        default=[
            SurfaceInitialState(),
            SurfaceInitialState(),
            SurfaceInitialState(),
        ],
        description="Initial states for roof layers",
    )
    walls: Optional[List[SurfaceInitialState]] = Field(
        default=[
            SurfaceInitialState(),
            SurfaceInitialState(),
            SurfaceInitialState(),
        ],
        description="Initial states for wall layers",
    )

    def to_df_state(self, grid_id: int) -> pd.DataFrame:
        """Convert initial states to DataFrame state format."""
        df_state = init_df_state(grid_id)

        # Add snowalb
        df_state[("snowalb", "0")] = self.snowalb.value

        # Add surface states
        surfaces = {
            "paved": self.paved,
            "bldgs": self.bldgs,
            "evetr": self.evetr,
            "dectr": self.dectr,
            "grass": self.grass,
            "bsoil": self.bsoil,
            "water": self.water,
        }
        # Add surface states
        for surface in surfaces.values():
            df_surface = surface.to_df_state(grid_id)
            df_state = pd.concat([df_state, df_surface], axis=1)

        # Add roof and wall states
        for facet_list, facet_type in [(self.roofs, "roof"), (self.walls, "wall")]:
            if facet_list is not None:  # Check for None explicitly
                for i, facet in enumerate(facet_list):
                    is_roof = facet_type == "roof"
                    df_facet = facet.to_df_state(grid_id, i, is_roof)
                    df_state = pd.concat([df_state, df_facet], axis=1)
                    df_state = df_state.sort_index(axis=1)

        # add dummy columns to conform to SUEWS convention
        list_cols = [
            "dqndt",
            "dqnsdt",
            "dt_since_start",
            "lenday_id",
            "qn_av",
            "qn_s_av",
            "tair_av",
            "tmax_id",
            "tmin_id",
            "tstep_prev",
            "snowfallcum",
        ]
        for col in list_cols:
            df_state[(col, "0")] = 0
            df_state = df_state.sort_index(axis=1)
        # special treatment for hdd_id
        for i in range(12):
            df_state[(f"hdd_id", f"({i},)")] = 0
            df_state = df_state.sort_index(axis=1)
        # Drop duplicate columns while preserving first occurrence
        df_state = df_state.loc[:, ~df_state.columns.duplicated(keep="first")]

        return df_state

    @classmethod
    def from_df_state(cls, df: pd.DataFrame, grid_id: int) -> "InitialStates":
        snowalb = df.loc[grid_id, ("snowalb", "0")]
        snowalb = ValueWithDOI[float](snowalb)

        surface_types = {
            "paved": InitialStatePaved,
            "bldgs": InitialStateBldgs,
            "evetr": InitialStateEvetr,
            "dectr": InitialStateDectr,
            "grass": InitialStateGrass,
            "bsoil": InitialStateBsoil,
            "water": InitialStateWater,
        }

        surfaces = {
            name: surface_class.from_df_state(df, grid_id, idx)
            for idx, (name, surface_class) in enumerate(surface_types.items())
        }

        def reconstruct_layers(
            layer_name: str, surface_class: Type[SurfaceInitialState], n_layers: int
        ) -> List[SurfaceInitialState]:
            layers = []
            for idx in range(n_layers):
                try:
                    layer = surface_class.from_df_state(df, grid_id, idx, layer_name)
                    layers.append(layer)
                except KeyError:
                    break
            return layers

        roofs = reconstruct_layers(
            "roof", SurfaceInitialState, len(cls.model_fields["roofs"].default)
        )
        walls = reconstruct_layers(
            "wall", SurfaceInitialState, len(cls.model_fields["walls"].default)
        )

        return cls(
            snowalb=snowalb,
            paved=surfaces["paved"],
            bldgs=surfaces["bldgs"],
            evetr=surfaces["evetr"],
            dectr=surfaces["dectr"],
            grass=surfaces["grass"],
            bsoil=surfaces["bsoil"],
            water=surfaces["water"],
            roofs=roofs,
            walls=walls,
        )


class ThermalLayers(BaseModel):
    dz: ValueWithDOI[List[float]] = Field(default=ValueWithDOI([0.1, 0.2, 0.3, 0.4, 0.5]))
    k: ValueWithDOI[List[float]] = Field(default=ValueWithDOI([1.0, 1.0, 1.0, 1.0, 1.0]))
    cp: ValueWithDOI[List[float]] = Field(default=ValueWithDOI([1000, 1000, 1000, 1000, 1000]))

    ref: Optional[Reference] = None

    def to_df_state(
        self,
        grid_id: int,
        idx: int,
        surf_type: Literal[
            "paved",
            "bldgs",
            "evetr",
            "dectr",
            "grass",
            "bsoil",
            "water",
            "roof",
            "wall",
        ],
    ) -> pd.DataFrame:
        """Convert thermal layer parameters to DataFrame state format.

        Args:
            grid_id: Grid ID for the DataFrame index
            surf_type: Surface type or facet type ("roof" or "wall")

        Returns:
            pd.DataFrame: DataFrame containing thermal layer parameters
        """
        df_state = init_df_state(grid_id)

        if surf_type == "roof":
            suffix = "roof"
        elif surf_type == "wall":
            suffix = "wall"
        else:
            suffix = "surf"

        # Add thermal layer parameters
        for i in range(5):
            df_state[(f"dz_{suffix}", f"({idx}, {i})")] = self.dz.value[i]
            df_state[(f"k_{suffix}", f"({idx}, {i})")] = self.k.value[i]
            df_state[(f"cp_{suffix}", f"({idx}, {i})")] = self.cp.value[i]

        return df_state

    @classmethod
    def from_df_state(
        cls,
        df: pd.DataFrame,
        grid_id: int,
        idx: int,
        surf_type: Union[SurfaceType, Literal["roof", "wall"]],
    ) -> "ThermalLayers":
        """Reconstruct ThermalLayers instance from DataFrame.

        Args:
            df: DataFrame containing thermal layer parameters.
            grid_id: Grid ID for the DataFrame index.
            idx: Surface index for identifying columns.
            surf_type: Surface type or facet type ("roof" or "wall").

        Returns:
            ThermalLayers: Reconstructed ThermalLayers instance.
        """
        dz = []
        k = []
        cp = []

        # Determine suffix based on surf_type
        if surf_type == "roof":
            suffix = "roof"
        elif surf_type == "wall":
            suffix = "wall"
        else:
            suffix = "surf"

        # Extract thermal layer parameters for each of the 5 layers
        for i in range(5):
            dz.append(df.loc[grid_id, (f"dz_{suffix}", f"({idx}, {i})")])
            k.append(df.loc[grid_id, (f"k_{suffix}", f"({idx}, {i})")])
            cp.append(df.loc[grid_id, (f"cp_{suffix}", f"({idx}, {i})")])

        # Convert to ValueWithDOI
        dz = ValueWithDOI[List[float]](dz)
        k = ValueWithDOI[List[float]](k)
        cp = ValueWithDOI[List[float]](cp)

        # Return reconstructed instance
        return cls(dz=dz, k=k, cp=cp)


class VegetationParams(BaseModel):
    porosity_id: ValueWithDOI[int]
    gdd_id: ValueWithDOI[int] = Field(description="Growing degree days ID")
    sdd_id: ValueWithDOI[int] = Field(description="Senescence degree days ID")
    lai: Dict[str, Union[ValueWithDOI[float], List[ValueWithDOI[float]]]] = Field(
        description="Leaf area index parameters"
    )
    ie_a: ValueWithDOI[float] = Field(description="Irrigation efficiency coefficient a")
    ie_m: ValueWithDOI[float] = Field(description="Irrigation efficiency coefficient m")

    ref: Optional[Reference] = None


class WaterDistribution(BaseModel):
    # Optional fields for all possible distributions
    to_paved: Optional[ValueWithDOI[float]] = Field(None, ge=0, le=1)
    to_bldgs: Optional[ValueWithDOI[float]] = Field(None, ge=0, le=1)
    to_dectr: Optional[ValueWithDOI[float]] = Field(None, ge=0, le=1)
    to_evetr: Optional[ValueWithDOI[float]] = Field(None, ge=0, le=1)
    to_grass: Optional[ValueWithDOI[float]] = Field(None, ge=0, le=1)
    to_bsoil: Optional[ValueWithDOI[float]] = Field(None, ge=0, le=1)
    to_water: Optional[ValueWithDOI[float]] = Field(None, ge=0, le=1)
    to_runoff: Optional[ValueWithDOI[float]] = Field(None, ge=0, le=1)  # For paved/bldgs
    to_soilstore: Optional[ValueWithDOI[float]] = Field(None, ge=0, le=1)  # For vegetated surfaces
    _surface_type: Optional[SurfaceType] = PrivateAttr(None)

    ref: Optional[Reference] = None

    def __init__(self, surface_type: Optional[SurfaceType] = None, **data):
        # Store surface type as private attribute
        super().__init__(**data)
        self._surface_type = surface_type

        # If surface type is provided, set default values
        if surface_type:
            self._set_defaults(surface_type)
            self.validate_distribution(surface_type)

    def _set_defaults(self, surface_type: SurfaceType):
        # Default distributions based on surface type
        default_distributions = {
            SurfaceType.PAVED: {
                "to_bldgs": ValueWithDOI(0.2),
                "to_evetr": ValueWithDOI(0.1),
                "to_dectr": ValueWithDOI(0.1),
                "to_grass": ValueWithDOI(0.1),
                "to_bsoil": ValueWithDOI(0.1),
                "to_water": ValueWithDOI(0.1),
                "to_runoff": ValueWithDOI(0.3),
            },
            SurfaceType.BLDGS: {
                "to_paved": ValueWithDOI(0.2),
                "to_evetr": ValueWithDOI(0.1),
                "to_dectr": ValueWithDOI(0.1),
                "to_grass": ValueWithDOI(0.1),
                "to_bsoil": ValueWithDOI(0.1),
                "to_water": ValueWithDOI(0.1),
                "to_runoff": ValueWithDOI(0.3),
            },
            SurfaceType.EVETR: {
                "to_paved": ValueWithDOI(0.1),
                "to_bldgs": ValueWithDOI(0.1),
                "to_dectr": ValueWithDOI(0.1),
                "to_grass": ValueWithDOI(0.1),
                "to_bsoil": ValueWithDOI(0.1),
                "to_water": ValueWithDOI(0.1),
                "to_soilstore": ValueWithDOI(0.4),
            },
            SurfaceType.DECTR: {
                "to_paved": ValueWithDOI(0.1),
                "to_bldgs": ValueWithDOI(0.1),
                "to_evetr": ValueWithDOI(0.1),
                "to_grass": ValueWithDOI(0.1),
                "to_bsoil": ValueWithDOI(0.1),
                "to_water": ValueWithDOI(0.1),
                "to_soilstore": ValueWithDOI(0.4),
            },
            SurfaceType.GRASS: {
                "to_paved": ValueWithDOI(0.1),
                "to_bldgs": ValueWithDOI(0.1),
                "to_dectr": ValueWithDOI(0.1),
                "to_evetr": ValueWithDOI(0.1),
                "to_bsoil": ValueWithDOI(0.1),
                "to_water": ValueWithDOI(0.1),
                "to_soilstore": ValueWithDOI(0.4),
            },
            SurfaceType.BSOIL: {
                "to_paved": ValueWithDOI(0.1),
                "to_bldgs": ValueWithDOI(0.1),
                "to_dectr": ValueWithDOI(0.1),
                "to_evetr": ValueWithDOI(0.1),
                "to_grass": ValueWithDOI(0.1),
                "to_water": ValueWithDOI(0.1),
                "to_soilstore": ValueWithDOI(0.4),
            },
        }

        if surface_type in default_distributions:
            defaults = default_distributions[surface_type]
            for key, value in defaults.items():
                if getattr(self, key) is None:
                    setattr(self, key, value)

    def validate_distribution(self, surface_type: SurfaceType) -> None:
        """Validate water distribution based on surface type"""
        # Define required fields for each surface type
        required_fields = {
            SurfaceType.PAVED: [
                "to_bldgs",
                "to_dectr",
                "to_evetr",
                "to_grass",
                "to_bsoil",
                "to_water",
                "to_runoff",
            ],
            SurfaceType.BLDGS: [
                "to_paved",
                "to_dectr",
                "to_evetr",
                "to_grass",
                "to_bsoil",
                "to_water",
                "to_runoff",
            ],
            SurfaceType.DECTR: [
                "to_paved",
                "to_bldgs",
                "to_evetr",
                "to_grass",
                "to_bsoil",
                "to_water",
                "to_soilstore",
            ],
            SurfaceType.EVETR: [
                "to_paved",
                "to_bldgs",
                "to_dectr",
                "to_grass",
                "to_bsoil",
                "to_water",
                "to_soilstore",
            ],
            SurfaceType.GRASS: [
                "to_paved",
                "to_bldgs",
                "to_dectr",
                "to_evetr",
                "to_bsoil",
                "to_water",
                "to_soilstore",
            ],
            SurfaceType.BSOIL: [
                "to_paved",
                "to_bldgs",
                "to_dectr",
                "to_evetr",
                "to_grass",
                "to_water",
                "to_soilstore",
            ],
            SurfaceType.WATER: None,  # Water surface doesn't have water distribution
        }

        if surface_type == SurfaceType.WATER:
            raise ValueError("Water surface should not have water distribution")

        fields = required_fields[surface_type]
        values = []

        # Check required fields are present and collect values
        for field in fields:
            value = getattr(self, field)
            if value is None:
                raise ValueError(
                    f"Missing required field {field} for {surface_type.value}"
                )
            values.append(value)

        # Validate sum
        total = sum(value.value if isinstance(value, ValueWithDOI) else value for value in values)
        # if not np.isclose(total, 1.0, rtol=1e-5):
        if not math.isclose(total, 1.0, rel_tol=1e-5):
            raise ValueError(f"Water distribution sum must be 1.0, got {total}")

    def to_df_state(self, grid_id: int, surf_idx: int) -> pd.DataFrame:
        """Convert water distribution parameters to DataFrame state format.

        Args:
            grid_id: Grid ID for the DataFrame index
            surf_idx: Surface index (0=paved, 1=bldgs, 2=dectr, 3=evetr, 4=grass, 5=bsoil, 6=water)

        Returns:
            pd.DataFrame: DataFrame containing water distribution parameters with MultiIndex columns
        """
        # Create tuples for MultiIndex columns
        param_tuples = []
        values = []

        # Add all non-None distribution parameters using a two-step process
        # 1. Collect all non-None values
        list_waterdist_value = []
        for i, attr in enumerate(
            [
                "to_paved",
                "to_bldgs",
                "to_evetr",
                "to_dectr",
                "to_grass",
                "to_bsoil",
                "to_water",
                # "to_soilstore",
                # "to_runoff",
            ]
        ):
            value = getattr(self, attr)
            if value is None:
                list_waterdist_value.append(0.0)
            else:
                list_waterdist_value.append(value)

        # either to_soilstore or to_runoff must be provided - the other must be 0
        to_soilstore_or_runoff = (
            self.to_runoff if self.to_soilstore is None else self.to_soilstore
        )
        list_waterdist_value.append(to_soilstore_or_runoff)

        # 2. Create param_tuples and values - only add non-None values following the order of the list
        for i, value in enumerate(list_waterdist_value):
            if value is not None:
                param_tuples.append(("waterdist", f"({i}, {surf_idx})"))
                values.append(value)

        # Create MultiIndex columns
        columns = pd.MultiIndex.from_tuples(param_tuples, names=["var", "ind_dim"])

        # Convert ValueWithDOI to float
        values = [value.value if isinstance(value, ValueWithDOI) else value for value in values]

        # Create DataFrame with single row
        df = pd.DataFrame(
            index=pd.Index([grid_id], name="grid"),
            columns=columns,
            data=[values],
            dtype=float,
        )

        return df

    @classmethod
    def from_df_state(
        cls, df: pd.DataFrame, grid_id: int, surf_idx: int
    ) -> "WaterDistribution":
        """
        Reconstruct WaterDistribution from a DataFrame state format.

        Args:
            df (pd.DataFrame): DataFrame containing water distribution parameters.
            grid_id (int): Grid ID for the DataFrame index.
            surf_idx (int): Surface index for identifying columns.

        Returns:
            WaterDistribution: Instance of WaterDistribution.
        """
        dict_surface_type = {
            0: SurfaceType.PAVED,
            1: SurfaceType.BLDGS,
            2: SurfaceType.EVETR,
            3: SurfaceType.DECTR,
            4: SurfaceType.GRASS,
            5: SurfaceType.BSOIL,
            6: SurfaceType.WATER,
        }
        surface_type = dict_surface_type[surf_idx]
        # initialize an instance of this class
        instance = cls(surface_type=surface_type)

        # Define the parameter names and their indices
        param_map = {
            "to_paved": 0,
            "to_bldgs": 1,
            "to_evetr": 2,
            "to_dectr": 3,
            "to_grass": 4,
            "to_bsoil": 5,
            "to_water": 6,
            # "to_soilstore": 7,
            # "to_runoff": 8,
        }

        # Extract the values from the DataFrame
        params = {
            param: df.loc[grid_id, ("waterdist", f"({idx}, {surf_idx})")]
            for param, idx in param_map.items()
        }
        for param, value in params.items():
            value = ValueWithDOI(value)
            if getattr(instance, param) is not None:
                setattr(instance, param, value)

        # set the last to_soilstore or to_runoff
        waterdist_last = df.loc[grid_id, ("waterdist", f"(7, {surf_idx})")]
        waterdist_last = ValueWithDOI(waterdist_last)
        if getattr(instance, "to_soilstore") is None:
            setattr(instance, "to_runoff", waterdist_last)
        else:
            setattr(instance, "to_soilstore", waterdist_last)

        return instance


class StorageDrainParams(BaseModel):
    store_min: ValueWithDOI[float] = Field(ge=0, default=ValueWithDOI(0.0))
    store_max: ValueWithDOI[float] = Field(ge=0, default=ValueWithDOI(10.0))
    store_cap: ValueWithDOI[float] = Field(ge=0, default=ValueWithDOI(10.0))
    drain_eq: ValueWithDOI[int] = Field(default=ValueWithDOI(0))
    drain_coef_1: ValueWithDOI[float] = Field(default=ValueWithDOI(0.013))
    drain_coef_2: ValueWithDOI[float] = Field(default=ValueWithDOI(1.71))

    ref: Optional[Reference] = None

    def to_df_state(self, grid_id: int, surf_idx: int) -> pd.DataFrame:
        """Convert storage and drain parameters to DataFrame state format.

        Args:
            grid_id: Grid ID for the DataFrame index
            surf_idx: Surface index (0=paved, 1=bldgs, 2=dectr, 3=evetr, 4=grass, 5=bsoil, 6=water)

        Returns:
            pd.DataFrame: DataFrame containing storage and drain parameters with MultiIndex columns
        """
        # Create tuples for MultiIndex columns
        param_tuples = [
            ("storedrainprm", f"({i}, {surf_idx})")
            for i, _ in enumerate(
                [
                    "store_min",
                    "drain_eq",
                    "drain_coef_1",
                    "drain_coef_2",
                    "store_max",
                    "store_cap",
                ]
            )
        ]

        # Create MultiIndex columns
        columns = pd.MultiIndex.from_tuples(param_tuples, names=["var", "ind_dim"])

        # Create DataFrame with single row
        df = pd.DataFrame(
            index=pd.Index([grid_id], name="grid"), columns=columns, dtype=float
        )

        # Fill values
        for i, var in enumerate(
            [
                "store_min",
                "drain_eq",
                "drain_coef_1",
                "drain_coef_2",
                "store_max",
                "store_cap",
            ]
        ):
            df.loc[grid_id, ("storedrainprm", f"({i}, {surf_idx})")] = getattr(
                self, var
            ).value

        return df

    @classmethod
    def from_df_state(
        cls, df: pd.DataFrame, grid_id: int, surf_idx: int
    ) -> "StorageDrainParams":
        """
        Reconstruct StorageDrainParams from DataFrame state format.

        Args:
            df: DataFrame containing storage and drain parameters.
            grid_id: Grid ID for the DataFrame index.
            surf_idx: Surface index (0=paved, 1=bldgs, 2=dectr, 3=evetr, 4=grass, 5=bsoil, 6=water).

        Returns:
            StorageDrainParams: Instance of StorageDrainParams.
        """
        # Define the parameter names and their indices
        param_map = {
            "store_min": 0,
            "drain_eq": 1,
            "drain_coef_1": 2,
            "drain_coef_2": 3,
            "store_max": 4,
            "store_cap": 5,
        }

        # Extract the values from the DataFrame
        params = {
            param: df.loc[grid_id, ("storedrainprm", f"({idx}, {surf_idx})")]
            for param, idx in param_map.items()
        }

        # Conver params to ValueWithDOI
        params = {key: ValueWithDOI(value) for key, value in params.items()}

        # Create an instance using the extracted parameters
        return cls(**params)


class OHMCoefficients(BaseModel):
    a1: ValueWithDOI[float] = Field(
        description="OHM coefficient a1 for different seasons and wetness conditions",
        default=ValueWithDOI(0.0),
    )
    a2: ValueWithDOI[float] = Field(
        description="OHM coefficient a2 for different seasons and wetness conditions",
        default=ValueWithDOI(0.0),
    )
    a3: ValueWithDOI[float] = Field(
        description="OHM coefficient a3 for different seasons and wetness conditions",
        default=ValueWithDOI(0.0),
    )

    ref: Optional[Reference] = None

    def to_df_state(self, grid_id: int, surf_idx: int, idx_s) -> pd.DataFrame:
        """Convert OHM coefficients to DataFrame state format.

        Args:
            grid_id (int): Grid ID
            surf_idx (int): Surface index

        Returns:
            pd.DataFrame: DataFrame containing OHM coefficients with MultiIndex columns
        """
        df_state = init_df_state(grid_id)

        # Map season/wetness combinations to indices
        a_map = {
            "a1": 0,
            "a2": 1,
            "a3": 2,
        }

        # Set values for each season/wetness combination
        for aX, idx_a in a_map.items():
            str_idx = f"({surf_idx}, {idx_s}, {idx_a})"
            df_state.loc[grid_id, ("ohm_coef", str_idx)] = getattr(self, aX).value

        return df_state
        
    @classmethod
    def from_df_state(
        cls, df: pd.DataFrame, grid_id: int, surf_idx: int, idx_s: int
    ) -> "OHMCoefficients":
        """
        Reconstruct OHMCoefficients from DataFrame state format.

        Args:
            df (pd.DataFrame): DataFrame containing OHM coefficients.
            grid_id (int): Grid ID.
            surf_idx (int): Surface index.

        Returns:
            OHMCoefficients: Reconstructed instance.
        """
        # Map coefficient to indices
        a_map = {
            "a1": 0,
            "a2": 1,
            "a3": 2
        }

        # Extract values for each season/wetness combination
        params = {
            aX: df.loc[
                grid_id, ("ohm_coef", f"({surf_idx}, {idx_s}, {idx})")
            ]
            for aX, idx in a_map.items()
        }

        # Convert to ValueWithDOI
        params = {key: ValueWithDOI(value) for key, value in params.items()}

        return cls(**params)


class OHM_Coefficient_season_wetness(BaseModel):
    summer_dry: OHMCoefficients = Field(
        description="OHM coefficient for summer dry conditions",
        default_factory=OHMCoefficients,
    )
    summer_wet: OHMCoefficients = Field(
        description="OHM coefficient for summer wet conditions",
        default_factory=OHMCoefficients,
    )
    winter_dry: OHMCoefficients = Field(
        description="OHM coefficient for winter dry conditions",
        default_factory=OHMCoefficients,
    )
    winter_wet: OHMCoefficients = Field(
        description="OHM coefficient for winter wet conditions",
        default_factory=OHMCoefficients,
    )

    ref: Optional[Reference] = None

    def to_df_state(self, grid_id: int, surf_idx: int) -> pd.DataFrame:
        """Convert OHM coefficients to DataFrame state format.

        Args:
            grid_id (int): Grid ID
            surf_idx (int): Surface index
            idx_a (int): Index for coefficient (0=a1, 1=a2, 2=a3)

        Returns:
            pd.DataFrame: DataFrame containing OHM coefficients with MultiIndex columns
        """
        df_state = init_df_state(grid_id)

        # Convert each coefficient
        for idx_s, coef in enumerate([self.summer_dry, self.summer_wet, self.winter_dry, self.winter_wet]):
            df_coef = coef.to_df_state(grid_id, surf_idx, idx_s)
            df_coef_extra = coef.to_df_state(
                grid_id, 7, idx_s
            )  # always include this extra row to conform to SUEWS convention
            df_state = pd.concat([df_state, df_coef, df_coef_extra], axis=1)

        # drop duplicate columns
        df_state = df_state.loc[:, ~df_state.columns.duplicated()]

        return df_state


    @classmethod
    def from_df_state(
        cls, df: pd.DataFrame, grid_id: int, surf_idx: int
    ) -> "OHM_Coefficient_season_wetness":
        """
        Reconstruct OHM_Coefficient_season_wetness from DataFrame state format.

        Args:
            df (pd.DataFrame): DataFrame containing OHM coefficients.
            grid_id (int): Grid ID.
            surf_idx (int): Surface index.
            idx_a (int): Index for coefficient (0=a1, 1=a2, 2=a3).

        Returns:
            OHM_Coefficient_season_wetness: Reconstructed instance.
        """

        summer_dry = OHMCoefficients.from_df_state(df, grid_id, surf_idx, 0)
        summer_wet = OHMCoefficients.from_df_state(df, grid_id, surf_idx, 1)
        winter_dry = OHMCoefficients.from_df_state(df, grid_id, surf_idx, 2)
        winter_wet = OHMCoefficients.from_df_state(df, grid_id, surf_idx, 3)

        return cls(
            summer_dry=summer_dry,
            summer_wet=summer_wet,
            winter_dry=winter_dry,
            winter_wet=winter_wet
        )


class SurfaceProperties(BaseModel):
    """Base properties for all surface types"""
    sfr: ValueWithDOI[float] = Field(ge=0, le=1, description="Surface fraction", default=ValueWithDOI(1.0 / 7))
    emis: ValueWithDOI[float] = Field(ge=0, le=1, description="Surface emissivity", default=ValueWithDOI(0.95))
    chanohm: Optional[ValueWithDOI[float]] = Field(default=ValueWithDOI(0.0))
    cpanohm: Optional[ValueWithDOI[float]] = Field(default=ValueWithDOI(1200.0))
    kkanohm: Optional[ValueWithDOI[float]] = Field(default=ValueWithDOI(0.4))
    ohm_threshsw: Optional[ValueWithDOI[float]] = Field(default=ValueWithDOI(0.0))
    ohm_threshwd: Optional[ValueWithDOI[float]] = Field(default=ValueWithDOI(0.0))
    ohm_coef: Optional[OHM_Coefficient_season_wetness] = Field(default_factory=OHM_Coefficient_season_wetness)
    soildepth: ValueWithDOI[float] = Field(default=ValueWithDOI(0.15))
    soilstorecap: ValueWithDOI[float] = Field(default=ValueWithDOI(150.0))
    statelimit: ValueWithDOI[float] = Field(default=ValueWithDOI(10.0))
    wetthresh: ValueWithDOI[float] = Field(default=ValueWithDOI(0.5))
    sathydraulicconduct: ValueWithDOI[float] = Field(default=ValueWithDOI(0.0001))
    waterdist: Optional[WaterDistribution] = Field(
        default=None, description="Water distribution parameters"
    )
    storedrainprm: StorageDrainParams = Field(
        default_factory=StorageDrainParams, description="Storage and drain parameters"
    )
    snowpacklimit: Optional[ValueWithDOI[float]] = Field(default=ValueWithDOI(10.0))
    thermal_layers: ThermalLayers = Field(
        default_factory=ThermalLayers, description="Thermal layers for the surface"
    )
    irrfrac: Optional[ValueWithDOI[float]] = Field(default=ValueWithDOI(0.0))
    _surface_type: Optional[SurfaceType] = PrivateAttr(default=None)

    ref: Optional[Reference] = None

    def set_surface_type(self, surface_type: SurfaceType):
        self._surface_type = surface_type
        if self._surface_type == SurfaceType.WATER:
            if self.waterdist is not None:
                raise ValueError("Water surface should not have water distribution")
        else:
            if self.waterdist is None:
                raise ValueError(
                    f"Water distribution required for {self._surface_type.value}"
                )
            self.waterdist.validate_distribution(self._surface_type)

    def get_surface_type(self) -> SurfaceType:
        return self._surface_type

    def get_surface_name(self) -> str:
        return self._surface_type.value

    def get_surface_index(self) -> int:
        dict_surface_type = {
            SurfaceType.PAVED: 0,
            SurfaceType.BLDGS: 1,
            SurfaceType.EVETR: 2,
            SurfaceType.DECTR: 3,
            SurfaceType.GRASS: 4,
            SurfaceType.BSOIL: 5,
            SurfaceType.WATER: 6,
        }
        return dict_surface_type[self._surface_type]

    def to_df_state(self, grid_id: int) -> pd.DataFrame:
        """Convert surface properties to DataFrame state format.
        This is the base implementation that handles common surface properties."""
        df_state = init_df_state(grid_id)

        # Get surface index
        surf_idx = self.get_surface_index()

        # Get surface name
        surf_name = self.get_surface_name()

        # Helper function to set values in DataFrame
        def set_df_value(col_name: str, value: float):
            idx_str = f"({surf_idx},)"
            if (col_name, idx_str) not in df_state.columns:
                # df_state[(col_name, idx_str)] = np.nan
                df_state[(col_name, idx_str)] = None
            df_state.loc[grid_id, (col_name, idx_str)] = value

        # Get all properties of this class using introspection
        properties = [
            "sfr",
            "emis",
            "chanohm",
            "cpanohm",
            "kkanohm",
            "ohm_coef",
            "ohm_threshsw",
            "ohm_threshwd",
            "soildepth",
            "soilstorecap",
            "statelimit",
            "wetthresh",
            "sathydraulicconduct",
            "waterdist",
            "storedrainprm",
            "snowpacklimit",
            "thermal_layers",
            "irrfrac",
        ]
        # drop 'surface_type' and model-specific properties (e.g. model_xx)
        properties = [
            p for p in properties if p != "surface_type" and not p.startswith("model_")
        ]

        # Process each property
        dfs = [df_state]  # List to collect all DataFrames

        for property in properties:
            # Handle nested properties with their own to_df_state methods
            if property in [
                "waterdist",
                "storedrainprm",
                "ohm_coef",
                "lai",
            ]:
                nested_obj = getattr(self, property)
                if nested_obj is not None and hasattr(nested_obj, "to_df_state"):
                    nested_df = nested_obj.to_df_state(grid_id, surf_idx)
                    dfs.append(nested_df)
            elif property == "thermal_layers":
                nested_df = self.thermal_layers.to_df_state(
                    grid_id, surf_idx, surf_name
                )
                dfs.append(nested_df)
            elif property == "irrfrac":
                value = getattr(self, property)
                value = value.value if isinstance(value, ValueWithDOI) else value
                df_state.loc[grid_id, (f"{property}{surf_name}", "0")] = value
            elif property in ["sfr", "soilstorecap", "statelimit", "wetthresh"]:
                value = getattr(self, property)
                value = value.value if isinstance(value, ValueWithDOI) else value
                set_df_value(f"{property}_surf", value)
            else:
                value = getattr(self, property)
                value = value.value if isinstance(value, ValueWithDOI) else value
                set_df_value(property, value)
            # except Exception as e:
            #     print(f"Warning: Could not set property {property}: {str(e)}")
            #     continue

        # add dummy columns to conform to SUEWS convention
        list_cols = [
            "ohm_threshsw",
            "ohm_threshwd",
        ]
        for col in list_cols:
            df_state[(col, "(7,)")] = 0

        # Merge all DataFrames
        df_final = pd.concat(dfs, axis=1).sort_index(axis=1)
        return df_final

    @classmethod
    def from_df_state(
        cls, df: pd.DataFrame, grid_id: int, surf_idx: int
    ) -> "SurfaceProperties":
        """Reconstruct surface properties from DataFrame state format."""

        # Get surface name
        surf_name = [
            "paved",
            "bldgs",
            "evetr",
            "dectr",
            "grass",
            "bsoil",
            "water",
        ][surf_idx]

        # Get all properties of this class using introspection
        properties = [
            "sfr",
            "emis",
            "chanohm",
            "cpanohm",
            "kkanohm",
            "ohm_threshsw",
            "ohm_threshwd",
            "soildepth",
            "soilstorecap",
            "statelimit",
            "wetthresh",
            "sathydraulicconduct",
            "waterdist",
            "storedrainprm",
            "snowpacklimit",
            "thermal_layers",
            "irrfrac",
        ]

        # drop 'surface_type' and model-specific properties (e.g. model_xx)
        properties = [
            p for p in properties if p != "surface_type" and not p.startswith("model_")
        ]

        # Create a dictionary to hold the properties and their values
        property_values = {}

        # Process each property
        for property in properties:
            # Handle nested properties with their own from_df_state methods
            if property in [
                "waterdist",
                "storedrainprm",
                "ohm_coef",
                "lai",
            ]:
                nested_obj = cls.model_fields[property].annotation
                if nested_obj is not None and hasattr(nested_obj, "from_df_state"):
                    property_values[property] = nested_obj.from_df_state(
                        df, grid_id, surf_idx
                    )
                continue
            elif property == "thermal_layers":
                property_values[property] = cls.model_fields[
                    "thermal_layers"
                ].annotation.from_df_state(df, grid_id, surf_idx, surf_name)
            elif property == "irrfrac":
                value = df.loc[grid_id, (f"{property}{surf_name}", "0")]
                property_values[property] = ValueWithDOI(value)
            elif property in ["sfr", "soilstorecap", "statelimit", "wetthresh"]:
                value = df.loc[grid_id, (f"{property}_surf", f"({surf_idx},)")]
                property_values[property] = ValueWithDOI(value)
            else:
                value = df.loc[grid_id, (property, f"({surf_idx},)")]
                property_values[property] = ValueWithDOI(value)

        return cls(**property_values)


class NonVegetatedSurfaceProperties(SurfaceProperties):
    alb: ValueWithDOI[float] = Field(ge=0, le=1, description="Surface albedo", default=ValueWithDOI(0.1))

    def to_df_state(self, grid_id: int) -> pd.DataFrame:
        """Convert non-vegetated surface properties to DataFrame state format."""

        # Get base properties from parent
        df_base = super().to_df_state(grid_id)

        surf_idx = self.get_surface_index()

        if self.waterdist is not None:
            df_waterdist = self.waterdist.to_df_state(grid_id, surf_idx)
            df_base = pd.concat([df_base, df_waterdist], axis=1).sort_index(axis=1)

        for attr in ["alb"]:
            df_base.loc[grid_id, (attr, f"({surf_idx},)")] = getattr(self, attr).value
            df_base = df_base.sort_index(axis=1)

        return df_base


class PavedProperties(NonVegetatedSurfaceProperties):  # May need to move VWD for waterdist to here for referencing
    _surface_type: Literal[SurfaceType.PAVED] = SurfaceType.PAVED
    waterdist: WaterDistribution = Field(
        default_factory=lambda: WaterDistribution(SurfaceType.PAVED),
        description="Water distribution fractions for paved surfaces",
    )

    def to_df_state(self, grid_id: int) -> pd.DataFrame:
        """Convert paved surface properties to DataFrame state format."""
        dfs = []

        # Get base properties from parent
        df_base = super().to_df_state(grid_id)
        dfs.append(df_base)

        surf_idx = self.get_surface_index()

        # Create DataFrame for this class's properties
        param_tuples = []
        values = []

        # Add all non-inherited properties that aren't model-specific or nested objects
        for attr in dir(self):
            if (
                not attr.startswith("_")
                and not callable(getattr(self, attr))
                and not attr.startswith("model_")
                and attr
                not in [
                    "_surface_type",
                    "waterdist",
                    "storedrainprm",
                    "thermal_layers",
                    "ohm_coef",
                ]
                and attr not in dir(super())
            ):
                value = getattr(self, attr)
                if not isinstance(value, (BaseModel, Enum)):
                    param_tuples.append((attr, (surf_idx,)))
                    values.append(value)

        if param_tuples:  # Only create DataFrame if we have properties to add
            columns = pd.MultiIndex.from_tuples(param_tuples, names=["var", "ind_dim"])
            df = pd.DataFrame(
                index=pd.Index([grid_id], name="grid"),
                columns=columns,
                data=[values],
                dtype=float,
            )
            dfs.append(df)

        # Add nested property DataFrames
        for nested_prop in ["waterdist", "storedrainprm", "thermal_layers", "ohm_coef"]:
            nested_obj = getattr(self, nested_prop)
            if nested_obj is not None and hasattr(nested_obj, "to_df_state"):
                if nested_prop == "thermal_layers":
                    surf_name = self.get_surface_name()
                    nested_df = nested_obj.to_df_state(grid_id, surf_idx, surf_name)
                else:
                    nested_df = nested_obj.to_df_state(grid_id, surf_idx)
                dfs.append(nested_df)

        # Merge all DataFrames
        df_final = pd.concat(dfs, axis=1)
        return df_final

    @classmethod
    def from_df_state(cls, df: pd.DataFrame, grid_id: int) -> "PavedProperties":
        """Reconstruct paved surface properties from DataFrame state format."""
        surf_idx = 0
        instance = super().from_df_state(df, grid_id, surf_idx)
        return instance


class BuildingLayer(BaseModel): # May need to move VWD for thermal layers here for referencing
    alb: ValueWithDOI[float] = Field(ge=0, le=1, description="Surface albedo", default=ValueWithDOI(0.1))
    emis: ValueWithDOI[float] = Field(ge=0, le=1, description="Surface emissivity", default=ValueWithDOI(0.95))
    thermal_layers: ThermalLayers = Field(
        default_factory=ThermalLayers, description="Thermal layers for the surface"
    )
    statelimit: ValueWithDOI[float] = Field(default=ValueWithDOI(10.0))
    soilstorecap: ValueWithDOI[float] = Field(default=ValueWithDOI(150.0))
    wetthresh: ValueWithDOI[float] = Field(default=ValueWithDOI(0.5))
    roof_albedo_dir_mult_fact: Optional[ValueWithDOI[float]] = Field(default=ValueWithDOI(0.1))
    wall_specular_frac: Optional[ValueWithDOI[float]] = Field(default=ValueWithDOI(0.1))
    _facet_type: Literal["roof", "wall"] = PrivateAttr(default="roof")

    ref: Optional[Reference] = None

    def to_df_state(
        self,
        grid_id: int,
        layer_idx: int,
        facet_type: Literal["roof", "wall"],
    ) -> pd.DataFrame:
        """Convert building layer parameters to DataFrame state format.

        Args:
            grid_id: Grid ID for the DataFrame index
            layer_idx: Layer index (0 or 1 for two layers)

        Returns:
            pd.DataFrame: DataFrame containing building layer parameters
        """
        df_state = init_df_state(grid_id)

        # Add basic parameters
        df_state[(f"alb_{facet_type}", f"({layer_idx},)")] = self.alb.value
        df_state[(f"emis_{facet_type}", f"({layer_idx},)")] = self.emis.value
        df_state[(f"statelimit_{facet_type}", f"({layer_idx},)")] = self.statelimit.value
        df_state[(f"soilstorecap_{facet_type}", f"({layer_idx},)")] = self.soilstorecap.value
        df_state[(f"wetthresh_{facet_type}", f"({layer_idx},)")] = self.wetthresh.value

        # Determine prefix based on layer type
        prefix = facet_type

        # Add layer-specific parameters
        if facet_type == "roof" and self.roof_albedo_dir_mult_fact is not None:
            df_state[(f"{prefix}_albedo_dir_mult_fact", f"(0, {layer_idx})")] = (
                self.roof_albedo_dir_mult_fact.value
            )
        elif facet_type == "wall" and self.wall_specular_frac is not None:
            df_state[(f"{prefix}_specular_frac", f"(0, {layer_idx})")] = (
                self.wall_specular_frac.value
            )

        # Add thermal layers
        df_thermal = self.thermal_layers.to_df_state(grid_id, layer_idx, facet_type)
        df_state = pd.concat([df_state, df_thermal], axis=1)

        return df_state

    @classmethod
    def from_df_state(
        cls,
        df: pd.DataFrame,
        grid_id: int,
        layer_idx: int,
        facet_type: Literal["roof", "wall"],
    ) -> "BuildingLayer":
        """Reconstruct BuildingLayer instance from DataFrame.

        Args:
            df: DataFrame containing building layer parameters.
            grid_id: Grid ID for the DataFrame index.
            layer_idx: Layer index (0 or 1 for two layers).
            facet_type: Facet type ("roof" or "wall").

        Returns:
            BuildingLayer: Reconstructed BuildingLayer instance.
        """
        # Prefix for the specific layer type
        prefix = facet_type

        # Extract scalar parameters
        params = {
            "alb": df.loc[grid_id, (f"alb_{prefix}", f"({layer_idx},)")],
            "emis": df.loc[grid_id, (f"emis_{prefix}", f"({layer_idx},)")],
            "statelimit": df.loc[grid_id, (f"statelimit_{prefix}", f"({layer_idx},)")],
            "soilstorecap": df.loc[
                grid_id, (f"soilstorecap_{prefix}", f"({layer_idx},)")
            ],
            "wetthresh": df.loc[grid_id, (f"wetthresh_{prefix}", f"({layer_idx},)")],
        }

        # Extract optional parameters
        if facet_type == "roof":
            params["roof_albedo_dir_mult_fact"] = df.loc[
                grid_id, (f"roof_albedo_dir_mult_fact", f"(0, {layer_idx})")
            ]

        elif facet_type == "wall":
            params["wall_specular_frac"] = df.loc[
                grid_id, (f"wall_specular_frac", f"(0, {layer_idx})")
            ]

        # Extract ThermalLayers
        thermal_layers = ThermalLayers.from_df_state(df, grid_id, layer_idx, facet_type)

        # Convert params to VWD - move below thermal_layers if needed
        params = {key: ValueWithDOI(value) for key, value in params.items()}

        # Add thermal_layers to params
        params["thermal_layers"] = thermal_layers

        # Return the reconstructed instance
        return cls(**params)


class RoofLayer(BuildingLayer):
    _facet_type: Literal["roof"] = "roof"


class WallLayer(BuildingLayer):
    _facet_type: Literal["wall"] = "wall"


class VerticalLayers(BaseModel):
    nlayer: ValueWithDOI[int] = Field(
        default=ValueWithDOI(3), description="Number of vertical layers in the urban canopy"
    )
    height: ValueWithDOI[List[float]] = Field(
        default=ValueWithDOI([0.0, 10.0, 20.0, 30.0]),
        description="Heights of layer boundaries in metres, length must be nlayer+1",
    )
    veg_frac: ValueWithDOI[List[float]] = Field(
        default=ValueWithDOI([0.0, 0.0, 0.0]),
        description="Fraction of vegetation in each layer, length must be nlayer",
    )
    veg_scale: ValueWithDOI[List[float]] = Field(
        default=ValueWithDOI([1.0, 1.0, 1.0]),
        description="Scaling factor for vegetation in each layer, length must be nlayer",
    )
    building_frac: ValueWithDOI[List[float]] = Field(
        default=ValueWithDOI([0.4, 0.3, 0.3]),
        description="Fraction of buildings in each layer, must sum to 1.0, length must be nlayer",
    )
    building_scale: ValueWithDOI[List[float]] = Field(
        default=ValueWithDOI([1.0, 1.0, 1.0]),
        description="Scaling factor for buildings in each layer, length must be nlayer",
    )
    roofs: List[RoofLayer] = Field(
        default_factory=lambda: [RoofLayer(), RoofLayer(), RoofLayer()],
        description="Properties for roof surfaces in each layer, length must be nlayer",
    )
    walls: List[WallLayer] = Field(
        default_factory=lambda: [WallLayer(), WallLayer(), WallLayer()],
        description="Properties for wall surfaces in each layer, length must be nlayer",
    )

    ref: Optional[Reference] = None

    @model_validator(mode="after")
    def validate_building(self) -> "VerticalLayers":
        # Validate building heights
        if len(self.height.value) != self.nlayer.value + 1:
            raise ValueError(
                f"Number of building heights ({len(self.height.value)}) must match nlayer+1 = ({self.nlayer.value+1})"
            )

        # Validate building fractions
        if len(self.building_frac.value) != self.nlayer.value:
            raise ValueError(
                f"Number of building fractions ({len(self.building_frac.value)}) must match nlayer ({self.nlayer.value})"
            )
        # This rule is not correct, we just need building_frac to be in range [0,1]
        # if not math.isclose(sum(self.building_frac), 1.0, rel_tol=1e-9):
        #    raise ValueError(
        #        f"Building fractions must sum to 1.0, got {sum(self.building_frac)}"
        #    )

        # Validate building scales
        if len(self.building_scale.value) != self.nlayer.value:
            raise ValueError(
                f"Number of building scales ({len(self.building_scale.value)}) must match nlayer ({self.nlayer.value})"
            )

        # Validate number of roof layers matches nlayer
        if len(self.roofs) != self.nlayer.value:
            raise ValueError(
                f"Number of roof layers ({len(self.roof)}) must match nlayer ({self.nlayer.value})"
            )

        # Validate number of wall layers matches nlayer
        if len(self.walls) != self.nlayer.value:
            raise ValueError(
                f"Number of wall layers ({len(self.wall)}) must match nlayer ({self.nlayer.value})"
            )

        return self

    def to_df_state(self, grid_id: int) -> pd.DataFrame:
        """Convert vertical layers to DataFrame state format."""
        # Initialize empty DataFrame with grid_id index
        df_state = init_df_state(grid_id)

        # Set number of vertical layers
        df_state[(f"nlayer", "0")] = self.nlayer.value

        # Set heights for each layer boundary (nlayer + 1 heights needed)
        for i in range(self.nlayer.value + 1):
            df_state[("height", f"({i},)")] = self.height.value[i]

        # Set vegetation and building parameters for each layer
        for var in ["veg_frac", "veg_scale", "building_frac", "building_scale"]:
            for i in range(self.nlayer.value):
                df_state[(f"{var}", f"({i},)")] = getattr(self, var).value[i]

        # Convert roof and wall properties to DataFrame format for each layer
        df_roofs = pd.concat(
            [self.roofs[i].to_df_state(grid_id, i, "roof") for i in range(self.nlayer.value)],
            axis=1,
        )
        df_walls = pd.concat(
            [self.walls[i].to_df_state(grid_id, i, "wall") for i in range(self.nlayer.value)],
            axis=1,
        )

        # Combine all DataFrames
        df_state = pd.concat([df_state, df_roofs, df_walls], axis=1)

        return df_state

    @classmethod
    def from_df_state(cls, df: pd.DataFrame, grid_id: int) -> "VerticalLayers":
        """Reconstruct VerticalLayers instance from DataFrame."""
        # Extract the number of layers
        nlayer = int(df.loc[grid_id, ("nlayer", "0")])

        # Extract heights for each layer boundary
        height = [df.loc[grid_id, ("height", f"({i},)")] for i in range(nlayer + 1)]

        # Extract vegetation and building parameters for each layer
        veg_frac = [df.loc[grid_id, ("veg_frac", f"({i},)")] for i in range(nlayer)]
        veg_scale = [df.loc[grid_id, ("veg_scale", f"({i},)")] for i in range(nlayer)]
        building_frac = [
            df.loc[grid_id, ("building_frac", f"({i},)")] for i in range(nlayer)
        ]
        building_scale = [
            df.loc[grid_id, ("building_scale", f"({i},)")] for i in range(nlayer)
        ]

        # Reconstruct roof and wall properties for each layer
        roofs = [RoofLayer.from_df_state(df, grid_id, i, "roof") for i in range(nlayer)]
        walls = [WallLayer.from_df_state(df, grid_id, i, "wall") for i in range(nlayer)]

        # Construct and return VerticalLayers instance
        return cls(
            nlayer=ValueWithDOI(nlayer),
            height=ValueWithDOI(height),
            veg_frac=ValueWithDOI(veg_frac),
            veg_scale=ValueWithDOI(veg_scale),
            building_frac=ValueWithDOI(building_frac),
            building_scale=ValueWithDOI(building_scale),
            roofs=roofs,
            walls=walls,
        )


class BldgsProperties(NonVegetatedSurfaceProperties): # May need to move VWD for waterdist to here for referencing
    _surface_type: Literal[SurfaceType.BLDGS] = SurfaceType.BLDGS
    faibldg: ValueWithDOI[float] = Field(
        ge=0, default=ValueWithDOI(0.3), description="Frontal area index of buildings"
    )
    bldgh: ValueWithDOI[float] = Field(
        ge=3, default=ValueWithDOI(10.0), description="Building height"
    )  # We need to check if there is a building - and then this has to be greather than 0, accordingly.
    waterdist: WaterDistribution = Field(
        default_factory=lambda: WaterDistribution(SurfaceType.BLDGS)
    )

    ref: Optional[Reference] = None

    @model_validator(mode="after")
    def validate_rsl_zd_range(self) -> "BldgsProperties":
        sfr_bldg_lower_limit = 0.18
        if self.sfr < sfr_bldg_lower_limit:
            if self.faibldg.value < 0.25 * (1 - self.sfr.value):
                raise ValueError(
                    "Frontal Area Index (FAI) is below a lower limit of: 0.25 * (1 - PAI), which is likely to cause a negative displacement height (zd) in the RSL.\n"
                    f"\tYou have entered a building FAI of {self.faibldg} and a building PAI of {self.sfr}.\n"
                    "\tFor more details, please refer to: https://github.com/UMEP-dev/SUEWS/issues/302"
                )
        return self

    def to_df_state(self, grid_id: int) -> pd.DataFrame:
        """Convert building properties to DataFrame state format."""
        df_state = super().to_df_state(grid_id).sort_index(axis=1)

        df_state.loc[grid_id, ("faibldg", "0")] = self.faibldg.value
        df_state = df_state.sort_index(axis=1)
        df_state.loc[grid_id, ("bldgh", "0")] = self.bldgh.value

        return df_state

    @classmethod
    def from_df_state(cls, df: pd.DataFrame, grid_id: int) -> "BldgsProperties":
        """Reconstruct building properties from DataFrame state format."""
        surf_idx = 1
        instance = super().from_df_state(df, grid_id, surf_idx)
        return instance


class BsoilProperties(NonVegetatedSurfaceProperties): # May need to move VWD for waterdist to here for referencing
    _surface_type: Literal[SurfaceType.BSOIL] = SurfaceType.BSOIL
    waterdist: WaterDistribution = Field(
        default_factory=lambda: WaterDistribution(SurfaceType.BSOIL),
        description="Water distribution for bare soil",
    )

    def to_df_state(self, grid_id: int) -> pd.DataFrame:
        """Convert bare soil properties to DataFrame state format."""
        df_state = super().to_df_state(grid_id)
        # df_state.loc[grid_id, ("waterdist", "0")] = self.waterdist
        return df_state

    @classmethod
    def from_df_state(cls, df: pd.DataFrame, grid_id: int) -> "BsoilProperties":
        """Reconstruct bare soil properties from DataFrame state format."""
        surf_idx = 5
        instance = super().from_df_state(df, grid_id, surf_idx)
        return instance


class WaterProperties(NonVegetatedSurfaceProperties):
    _surface_type: Literal[SurfaceType.WATER] = SurfaceType.WATER
    flowchange: ValueWithDOI[float] = Field(default=ValueWithDOI(0.0))

    def to_df_state(self, grid_id: int) -> pd.DataFrame:
        """Convert water surface properties to DataFrame state format."""
        df_state = super().to_df_state(grid_id)
        surf_idx = self.get_surface_index()

        # Helper function to set values in DataFrame
        def set_df_value(col_name: str, value: float):
            idx_str = f"({surf_idx},)"
            if (col_name, idx_str) not in df_state.columns:
                # df_state[(col_name, idx_str)] = np.nan
                df_state[(col_name, idx_str)] = None
            df_state.loc[grid_id, (col_name, idx_str)] = value

        list_attr = ["flowchange"]

        # Add all non-inherited properties
        df_state.loc[grid_id, ("flowchange", "0")] = self.flowchange.value

        return df_state

    @classmethod
    def from_df_state(cls, df: pd.DataFrame, grid_id: int) -> "WaterProperties":
        """Reconstruct water properties from DataFrame state format."""
        surf_idx = 6
        instance = super().from_df_state(df, grid_id, surf_idx)
        return instance


class ModelControl(BaseModel):
    tstep: int = Field(
        default=300, description="Time step in seconds for model calculations"
    )
    forcing_file: ValueWithDOI[str] = Field(
        default=ValueWithDOI("forcing.txt"), description="Path to meteorological forcing data file"
    )
    output_file: str = Field(
        default="output.txt", description="Path to model output file"
    )
    # daylightsaving_method: int
    diagnose: int = Field(
        default=0,
        description="Level of diagnostic output (0=none, 1=basic, 2=detailed)",
    )

    ref: Optional[Reference] = None

    def to_df_state(self, grid_id: int) -> pd.DataFrame:
        """Convert model control properties to DataFrame state format."""
        df_state = init_df_state(grid_id)

        # Helper function to set values in DataFrame
        def set_df_value(col_name: str, value: float):
            idx_str = "0"
            if (col_name, idx_str) not in df_state.columns:
                # df_state[(col_name, idx_str)] = np.nan
                df_state[(col_name, idx_str)] = None
            df_state.at[grid_id, (col_name, idx_str)] = value

        list_attr = ["tstep", "diagnose"]
        for attr in list_attr:
            set_df_value(attr, getattr(self, attr))
        return df_state

    @classmethod
    def from_df_state(cls, df: pd.DataFrame, grid_id: int) -> "ModelControl":
        """Reconstruct model control properties from DataFrame state format."""
        instance = cls()
        for attr in ["tstep", "diagnose"]:
            setattr(instance, attr, df.loc[grid_id, (attr, "0")])
        return instance


class ModelPhysics(BaseModel):
    netradiationmethod: ValueWithDOI[int] = Field(
        default=ValueWithDOI(3), description="Method used to calculate net radiation"
    )
    emissionsmethod: ValueWithDOI[int] = Field(
        default=ValueWithDOI(2), description="Method used to calculate anthropogenic emissions"
    )
    storageheatmethod: ValueWithDOI[int] = Field(
        default=ValueWithDOI(1), description="Method used to calculate storage heat flux"
    )
    ohmincqf: ValueWithDOI[int] = Field(
        default=ValueWithDOI(0),
        description="Include anthropogenic heat in OHM calculations (1) or not (0)",
    )
    roughlenmommethod: ValueWithDOI[int] = Field(
        default=ValueWithDOI(2), description="Method used to calculate momentum roughness length"
    )
    roughlenheatmethod: ValueWithDOI[int] = Field(
        default=ValueWithDOI(2), description="Method used to calculate heat roughness length"
    )
    stabilitymethod: ValueWithDOI[int] = Field(
        default=ValueWithDOI(2), description="Method used for atmospheric stability calculation"
    )
    smdmethod: ValueWithDOI[int] = Field(
        default=ValueWithDOI(1), description="Method used to calculate soil moisture deficit"
    )
    waterusemethod: ValueWithDOI[int] = Field(
        default=ValueWithDOI(1), description="Method used to calculate water use"
    )
    diagmethod: ValueWithDOI[int] = Field(default=ValueWithDOI(1), description="Method used for model diagnostics")
    faimethod: ValueWithDOI[int] = Field(
        default=ValueWithDOI(1), description="Method used to calculate frontal area index"
    )
    localclimatemethod: ValueWithDOI[int] = Field(
        default=ValueWithDOI(0), description="Method used for local climate zone calculations"
    )
    snowuse: ValueWithDOI[int] = Field(
        default=ValueWithDOI(0), description="Include snow calculations (1) or not (0)"
    )
    stebbsmethod: ValueWithDOI[int] = Field(
        default=ValueWithDOI(0), description="Method used for stebbs calculations"
    )

    ref: Optional[Reference] = None

    @model_validator(mode="after")
    def check_storageheatmethod(self) -> "ModelPhysics":
        if self.storageheatmethod == 1 and self.ohmincqf != 0:
            raise ValueError(
                f"\nStorageHeatMethod is set to {self.storageheatmethod} and OhmIncQf is set to {self.ohmincqf}.\n"
                f"You should switch to OhmIncQf=0.\n"
            )
        elif self.storageheatmethod == 2 and self.ohmincqf != 1:
            raise ValueError(
                f"\nStorageHeatMethod is set to {self.storageheatmethod} and OhmIncQf is set to {self.ohmincqf}.\n"
                f"You should switch to OhmIncQf=1.\n"
            )
        return self

    @model_validator(mode="after")
    def check_snowusemethod(self) -> "ModelPhysics":
        if self.snowuse == 1:
            raise ValueError(
                f"\nSnowUse is set to {self.snowuse}.\n"
                f"There are no checks implemented for this case (snow calculations included in the run).\n"
                f"You should switch to SnowUse=0.\n"
            )
        return self

    # We then need to set to 0 (or None) all the snow-related parameters or rules
    # in the code and return them accordingly in the yml file.

    @model_validator(mode="after")
    def check_emissionsmethod(self) -> "ModelPhysics":
        if self.emissionsmethod == 45:
            raise ValueError(
                f"\nEmissionsMethod is set to {self.emissionsmethod}.\n"
                f"There are no checks implemented for this case (CO2 calculations included in the run).\n"
                f"You should switch to EmissionsMethod=0, 1, 2, 3, or 4.\n"
            )
        return self

    # We then need to set to 0 (or None) all the CO2-related parameters or rules
    # in the code and return them accordingly in the yml file.

    def to_df_state(self, grid_id: int) -> pd.DataFrame:
        """Convert model physics properties to DataFrame state format."""
        df_state = init_df_state(grid_id)

        # Helper function to set values in DataFrame
        def set_df_value(col_name: str, value: float):
            idx_str = "0"
            if (col_name, idx_str) not in df_state.columns:
                # df_state[(col_name, idx_str)] = np.nan
                df_state[(col_name, idx_str)] = None
            df_state.at[grid_id, (col_name, idx_str)] = int(value.value)

        list_attr = [
            "netradiationmethod",
            "emissionsmethod",
            "storageheatmethod",
            "ohmincqf",
            "roughlenmommethod",
            "roughlenheatmethod",
            "stabilitymethod",
            "smdmethod",
            "waterusemethod",
            "diagmethod",
            "faimethod",
            "localclimatemethod",
            "snowuse",
            "stebbsmethod",
        ]
        for attr in list_attr:
            set_df_value(attr, getattr(self, attr))
        return df_state

    @classmethod
    def from_df_state(cls, df: pd.DataFrame, grid_id: int) -> "ModelPhysics":
        """
        Reconstruct ModelPhysics from a DataFrame state format.

        Args:
            df: DataFrame containing model physics properties
            grid_id: Grid ID for the DataFrame index

        Returns:
            ModelPhysics: Instance of ModelPhysics
        """

        properties = {}

        list_attr = [
            "netradiationmethod",
            "emissionsmethod",
            "storageheatmethod",
            "ohmincqf",
            "roughlenmommethod",
            "roughlenheatmethod",
            "stabilitymethod",
            "smdmethod",
            "waterusemethod",
            "diagmethod",
            "faimethod",
            "localclimatemethod",
            "snowuse",
            "stebbsmethod",
        ]

        for attr in list_attr:
            try:
                properties[attr] = ValueWithDOI(int(df.loc[grid_id, (attr, "0")]))
            except KeyError:
                raise ValueError(f"Missing attribute '{attr}' in the DataFrame")

        return cls(**properties)


class LUMPSParams(BaseModel):
    raincover: ValueWithDOI[float] = Field(ge=0, le=1, default=ValueWithDOI(0.25))
    rainmaxres: ValueWithDOI[float] = Field(ge=0, le=20, default=ValueWithDOI(0.25))
    drainrt: ValueWithDOI[float] = Field(ge=0, le=1, default=ValueWithDOI(0.25))
    veg_type: ValueWithDOI[int] = Field(default=ValueWithDOI(1))

    ref: Optional[Reference] = None

    def to_df_state(self, grid_id: int) -> pd.DataFrame:
        """Convert LUMPS parameters to DataFrame state format.

        Args:
            grid_id: Grid ID for the DataFrame index

        Returns:
            pd.DataFrame: DataFrame containing LUMPS parameters
        """
        df_state = init_df_state(grid_id)

        # Add all attributes
        for attr in ["raincover", "rainmaxres", "drainrt", "veg_type"]:
            df_state[(attr, "0")] = getattr(self, attr).value

        return df_state

    @classmethod
    def from_df_state(cls, df: pd.DataFrame, grid_id: int) -> "LUMPSParams":
        """Create LUMPSParams from DataFrame state format.

        Args:
            df: DataFrame containing LUMPS parameters
            grid_id: Grid ID for the DataFrame index

        Returns:
            LUMPSParams: Instance of LUMPSParams
        """
        # Extract attributes from DataFrame
        params = {}
        for attr in ["raincover", "rainmaxres", "drainrt", "veg_type"]:
            params[attr] = df.loc[grid_id, (attr, "0")]

        # Convert attributes to ValueWithDOI
        params = {key: ValueWithDOI(value) for key, value in params.items()}

        return cls(**params)


class SPARTACUSParams(BaseModel):
    air_ext_lw: ValueWithDOI[float] = Field(
        default=ValueWithDOI(0.0), description="Air extinction coefficient for longwave radiation"
    )
    air_ext_sw: ValueWithDOI[float] = Field(
        default=ValueWithDOI(0.0), description="Air extinction coefficient for shortwave radiation"
    )
    air_ssa_lw: ValueWithDOI[float] = Field(
        default=ValueWithDOI(0.5), description="Air single scattering albedo for longwave radiation"
    )
    air_ssa_sw: ValueWithDOI[float] = Field(
        default=ValueWithDOI(0.5), description="Air single scattering albedo for shortwave radiation"
    )
    ground_albedo_dir_mult_fact: ValueWithDOI[float] = Field(
        default=ValueWithDOI(1.0), description="Multiplication factor for direct ground albedo"
    )
    n_stream_lw_urban: ValueWithDOI[int] = Field(
        default=ValueWithDOI(2), description="Number of streams for longwave radiation in urban areas"
    )
    n_stream_sw_urban: ValueWithDOI[int] = Field(
        default=ValueWithDOI(2),
        description="Number of streams for shortwave radiation in urban areas",
    )
    n_vegetation_region_urban: ValueWithDOI[int] = Field(
        default=ValueWithDOI(1), description="Number of vegetation regions in urban areas"
    )
    sw_dn_direct_frac: ValueWithDOI[float] = Field(
        default=ValueWithDOI(0.5),
        description="Fraction of downward shortwave radiation that is direct",
    )
    use_sw_direct_albedo: ValueWithDOI[float] = Field(
        default=ValueWithDOI(1.0), description="Flag to use direct albedo for shortwave radiation"
    )
    veg_contact_fraction_const: ValueWithDOI[float] = Field(
        default=ValueWithDOI(0.5), description="Constant vegetation contact fraction"
    )
    veg_fsd_const: ValueWithDOI[float] = Field(
        default=ValueWithDOI(0.5), description="Constant vegetation fractional standard deviation"
    )
    veg_ssa_lw: ValueWithDOI[float] = Field(
        default=ValueWithDOI(0.5),
        description="Vegetation single scattering albedo for longwave radiation",
    )
    veg_ssa_sw: ValueWithDOI[float] = Field(
        default=ValueWithDOI(0.5),
        description="Vegetation single scattering albedo for shortwave radiation",
    )

    ref: Optional[Reference] = None

    def to_df_state(self, grid_id: int) -> pd.DataFrame:
        """
        Convert SPARTACUS parameters to DataFrame state format.

        Args:
            grid_id: Grid ID for the DataFrame index

        Returns:
            pd.DataFrame: DataFrame containing SPARTACUS parameters
        """
        # Initialize DataFrame with grid index
        df_state = init_df_state(grid_id)

        # Map SPARTACUS parameters to DataFrame columns
        spartacus_params = {
            "air_ext_lw": self.air_ext_lw,
            "air_ext_sw": self.air_ext_sw,
            "air_ssa_lw": self.air_ssa_lw,
            "air_ssa_sw": self.air_ssa_sw,
            "ground_albedo_dir_mult_fact": self.ground_albedo_dir_mult_fact,
            "n_stream_lw_urban": self.n_stream_lw_urban,
            "n_stream_sw_urban": self.n_stream_sw_urban,
            "n_vegetation_region_urban": self.n_vegetation_region_urban,
            "sw_dn_direct_frac": self.sw_dn_direct_frac,
            "use_sw_direct_albedo": self.use_sw_direct_albedo,
            "veg_contact_fraction_const": self.veg_contact_fraction_const,
            "veg_fsd_const": self.veg_fsd_const,
            "veg_ssa_lw": self.veg_ssa_lw,
            "veg_ssa_sw": self.veg_ssa_sw,
        }

        # Assign each parameter to its corresponding column in the DataFrame
        for param_name, value in spartacus_params.items():
            df_state[(param_name, "0")] = value.value

        return df_state

    @classmethod
    def from_df_state(cls, df: pd.DataFrame, grid_id: int) -> "SPARTACUSParams":
        """
        Reconstruct SPARTACUSParams from DataFrame state format.

        Args:
            df: DataFrame containing SPARTACUS parameters
            grid_id: Grid ID for the DataFrame index

        Returns:
            SPARTACUSParams: An instance of SPARTACUSParams
        """

        spartacus_params = {
            "air_ext_lw",
            "air_ext_sw",
            "air_ssa_lw",
            "air_ssa_sw",
            "ground_albedo_dir_mult_fact",
            "n_stream_lw_urban",
            "n_stream_sw_urban",
            "n_vegetation_region_urban",
            "sw_dn_direct_frac",
            "use_sw_direct_albedo",
            "veg_contact_fraction_const",
            "veg_fsd_const",
            "veg_ssa_lw",
            "veg_ssa_sw",
        }

        params = {param: ValueWithDOI(df.loc[grid_id, (param, "0")]) for param in spartacus_params}

        return cls(**params)


class DayProfile(BaseModel):
    working_day: float = Field(default=1.0)
    holiday: float = Field(default=0.0)

    ref: Optional[Reference] = None

    def to_df_state(self, grid_id: int, param_name: str) -> pd.DataFrame:
        """
        Convert day profile to DataFrame state format.

        Args:
            grid_id (int): Grid ID for the DataFrame index.
            param_name (str): Name of the parameter this profile belongs to.

        Returns:
            pd.DataFrame: DataFrame containing day profile parameters.
        """

        df_state = init_df_state(grid_id)

        day_map = {
            "working_day": 0,
            "holiday": 1,
        }

        for day, idx in day_map.items():
            df_state.loc[grid_id, (param_name, f"({idx},)")] = getattr(self, day)

        return df_state

    @classmethod
    def from_df_state(
        cls, df: pd.DataFrame, grid_id: int, param_name: str
    ) -> "DayProfile":
        """
        Reconstruct DayProfile from a DataFrame state format.

        Args:
            df (pd.DataFrame): DataFrame containing day profile parameters.
            grid_id (int): Grid ID for the DataFrame index.
            param_name (str): Name of the parameter this profile belongs to.

        Returns:
            DayProfile: Instance of DayProfile.
        """

        day_map = {
            "working_day": 0,
            "holiday": 1,
        }

        # Extract values for working day and holiday from the DataFrame
        params = {}
        for day, idx in day_map.items():
            col = (param_name, f"({idx},)")
            if col in df.columns:
                params[day] = df.loc[grid_id, col]
            else:
                raise KeyError(f"Column {col} not found in DataFrame")

        return cls(**params)


class WeeklyProfile(BaseModel):
    monday: float = 0.0
    tuesday: float = 0.0
    wednesday: float = 0.0
    thursday: float = 0.0
    friday: float = 0.0
    saturday: float = 0.0
    sunday: float = 0.0

    ref: Optional[Reference] = None

    def to_df_state(self, grid_id: int, param_name: str) -> pd.DataFrame:
        """Convert weekly profile to DataFrame state format.

        Args:
            grid_id: Grid ID for the DataFrame index
            param_name: Name of the parameter this profile belongs to

        Returns:
            pd.DataFrame: DataFrame containing weekly profile parameters
        """
        df_state = init_df_state(grid_id)

        # Map days to their index
        day_map = {
            "monday": 0,
            "tuesday": 1,
            "wednesday": 2,
            "thursday": 3,
            "friday": 4,
            "saturday": 5,
            "sunday": 6,
        }

        for day, idx in day_map.items():
            df_state[(param_name, f"({idx},)")] = getattr(self, day)

        return df_state

    @classmethod
    def from_df_state(
        cls, df: pd.DataFrame, grid_id: int, param_name: str
    ) -> "WeeklyProfile":
        """Reconstruct WeeklyProfile from a DataFrame state format.

        Args:
            df: DataFrame containing weekly profile parameters
            grid_id: Grid ID for the DataFrame index
            param_name: Name of the parameter to extract values from

        Returns:
            WeeklyProfile: Instance of WeeklyProfile
        """
        # Map days to their index
        day_map = {
            "monday": 0,
            "tuesday": 1,
            "wednesday": 2,
            "thursday": 3,
            "friday": 4,
            "saturday": 5,
            "sunday": 6,
        }

        # Extract values from DataFrame for each day
        params = {
            day: df.loc[grid_id, (param_name, f"({idx},)")]
            for day, idx in day_map.items()
        }

        # Create an instance of WeeklyProfile
        return cls(**params)


class HourlyProfile(BaseModel):
    working_day: Dict[str, float]
    holiday: Dict[str, float]

    ref: Optional[Reference] = None

    @classmethod
    def __init_default_values__(cls) -> Dict[str, Dict[str, float]]:
        """Generate default values for hourly profiles.

        Returns:
            Dict containing default working_day and holiday profiles with uniform distribution
        """
        # Create uniform distribution (1/24) for each hour
        uniform_value = 1.0 / 24.0

        # Generate hour keys 1-24 with uniform values
        hourly_values = {str(hour): uniform_value for hour in range(1, 25)}

        return {"working_day": hourly_values.copy(), "holiday": hourly_values.copy()}

    def __init__(self, **data):
        # If no values provided, use defaults
        if not data:
            defaults = self.__init_default_values__()
            data = defaults
        super().__init__(**data)

    @field_validator("working_day", "holiday", mode="before")
    def convert_keys_to_str(cls, v: Dict) -> Dict[str, float]:
        if isinstance(v, dict):
            return {str(k): float(v) for k, v in v.items()}
        return v

    @model_validator(mode="after")
    def validate_hours(self) -> "HourlyProfile":
        for profile in [self.working_day, self.holiday]:
            hours = [int(h) for h in profile.keys()]
            if not all(1 <= h <= 24 for h in hours):
                raise ValueError("Hour values must be between 1 and 24")
            if sorted(hours) != list(range(1, 25)):
                error_message = ValueError("Must have all hours from 1 to 24")
                raise ValueError("Must have all hours from 1 to 24")
        return self

    def to_df_state(self, grid_id: int, param_name: str) -> pd.DataFrame:
        """Convert hourly profile to DataFrame state format.

        Args:
            grid_id: Grid ID for the DataFrame index
            param_name: Name of the parameter this profile belongs to

        Returns:
            pd.DataFrame: DataFrame containing hourly profile parameters
        """
        df_state = init_df_state(grid_id)

        # Set working day values (index 0)
        for hour, value in self.working_day.items():
            df_state[(param_name, f"({int(hour)-1}, 0)")] = value

        # Set holiday/weekend values (index 1)
        for hour, value in self.holiday.items():
            df_state[(param_name, f"({int(hour)-1}, 1)")] = value

        return df_state

    @classmethod
    def from_df_state(
        cls, df: pd.DataFrame, grid_id: int, param_name: str
    ) -> "HourlyProfile":
        """Reconstruct HourlyProfile from a DataFrame state format.

        Args:
            df: DataFrame containing hourly profile parameters
            grid_id: Grid ID for the DataFrame index
            param_name: Name of the parameter to extract values from

        Returns:
            HourlyProfile: Instance of HourlyProfile
        """
        # Extract working day values (index 0)
        working_day = {
            str(hour + 1): df.loc[grid_id, (param_name, f"({hour}, 0)")]
            for hour in range(24)
        }

        # Extract holiday values (index 1)
        holiday = {
            str(hour + 1): df.loc[grid_id, (param_name, f"({hour}, 1)")]
            for hour in range(24)
        }

        # Create an instance of HourlyProfile
        return cls(working_day=working_day, holiday=holiday)


class IrrigationParams(BaseModel): # TODO: May need to add ValueWithDOI to the profiles here
    h_maintain: ValueWithDOI[float] = Field(
        default=ValueWithDOI(0.5), description="Soil moisture threshold for irrigation"
    )
    faut: ValueWithDOI[float] = Field(default=ValueWithDOI(0.0), description="Fraction of automatic irrigation")
    ie_start: ValueWithDOI[float] = Field(default=ValueWithDOI(0.0), description="Start time of irrigation (hour)")
    ie_end: ValueWithDOI[float] = Field(default=ValueWithDOI(0.0), description="End time of irrigation (hour)")
    internalwateruse_h: ValueWithDOI[float] = Field(
        default=ValueWithDOI(0.0), description="Internal water use per hour"
    )
    daywatper: WeeklyProfile = Field(default_factory=WeeklyProfile)
    daywat: WeeklyProfile = Field(default_factory=WeeklyProfile)
    wuprofa_24hr: HourlyProfile = Field(default_factory=HourlyProfile)
    wuprofm_24hr: HourlyProfile = Field(default_factory=HourlyProfile)

    ref: Optional[Reference] = None

    def to_df_state(self, grid_id: int) -> pd.DataFrame:
        """
        Convert irrigation parameters to DataFrame state format.

        Args:
            grid_id: Grid ID for the DataFrame index

        Returns:
            pd.DataFrame: DataFrame containing irrigation parameters
        """

        df_state = init_df_state(grid_id)

        df_state.loc[grid_id, ("h_maintain", "0")] = self.h_maintain.value
        df_state.loc[grid_id, ("faut", "0")] = self.faut.value
        df_state.loc[grid_id, ("ie_start", "0")] = self.ie_start.value
        df_state.loc[grid_id, ("ie_end", "0")] = self.ie_end.value
        df_state.loc[grid_id, ("internalwateruse_h", "0")] = self.internalwateruse_h.value

        df_daywatper = self.daywatper.to_df_state(grid_id, "daywatper")
        df_daywat = self.daywat.to_df_state(grid_id, "daywat")

        df_state = df_state.combine_first(df_daywatper)
        df_state = df_state.combine_first(df_daywat)

        df_wuprofa_24hr = self.wuprofa_24hr.to_df_state(grid_id, "wuprofa_24hr")
        df_wuprofm_24hr = self.wuprofm_24hr.to_df_state(grid_id, "wuprofm_24hr")

        df_state = df_state.combine_first(df_wuprofa_24hr)
        df_state = df_state.combine_first(df_wuprofm_24hr)

        return df_state

    @classmethod
    def from_df_state(cls, df: pd.DataFrame, grid_id: int) -> "IrrigationParams":
        """
        Reconstruct IrrigationParams from a DataFrame state format.

        Args:
            df: DataFrame containing irrigation parameters
            grid_id: Grid ID for the DataFrame index

        Returns:
            IrrigationParams: Instance of IrrigationParams
        """
        # Extract scalar attributes
        h_maintain = df.loc[grid_id, ("h_maintain", "0")]
        faut = df.loc[grid_id, ("faut", "0")]
        ie_start = df.loc[grid_id, ("ie_start", "0")]
        ie_end = df.loc[grid_id, ("ie_end", "0")]
        internalwateruse_h = df.loc[grid_id, ("internalwateruse_h", "0")]

        # Conver to ValueWithDOI
        h_maintain = ValueWithDOI(h_maintain)
        faut = ValueWithDOI(faut)
        ie_start = ValueWithDOI(ie_start)
        ie_end = ValueWithDOI(ie_end)
        internalwateruse_h = ValueWithDOI(internalwateruse_h)

        # Extract WeeklyProfile attributes
        daywatper = WeeklyProfile.from_df_state(df, grid_id, "daywatper")
        daywat = WeeklyProfile.from_df_state(df, grid_id, "daywat")

        # Extract HourlyProfile attributes
        wuprofa_24hr = HourlyProfile.from_df_state(df, grid_id, "wuprofa_24hr")
        wuprofm_24hr = HourlyProfile.from_df_state(df, grid_id, "wuprofm_24hr")

        # Construct and return the IrrigationParams instance
        return cls(
            h_maintain=h_maintain,
            faut=faut,
            ie_start=ie_start,
            ie_end=ie_end,
            internalwateruse_h=internalwateruse_h,
            daywatper=daywatper,
            daywat=daywat,
            wuprofa_24hr=wuprofa_24hr,
            wuprofm_24hr=wuprofm_24hr,
        )


class AnthropogenicHeat(BaseModel): # TODO: May need to add the ValueWithDOI to the profiles here
    qf0_beu: DayProfile = Field(
        description="Base anthropogenic heat flux for buildings, equipment and urban metabolism",
        default_factory=DayProfile,
    )
    qf_a: DayProfile = Field(
        description="Coefficient a for anthropogenic heat flux calculation",
        default_factory=DayProfile,
    )
    qf_b: DayProfile = Field(
        description="Coefficient b for anthropogenic heat flux calculation",
        default_factory=DayProfile,
    )
    qf_c: DayProfile = Field(
        description="Coefficient c for anthropogenic heat flux calculation",
        default_factory=DayProfile,
    )
    baset_cooling: DayProfile = Field(
        description="Base temperature for cooling degree days",
        default_factory=DayProfile,
    )
    baset_heating: DayProfile = Field(
        description="Base temperature for heating degree days",
        default_factory=DayProfile,
    )
    ah_min: DayProfile = Field(
        description="Minimum anthropogenic heat flux", default_factory=DayProfile
    )
    ah_slope_cooling: DayProfile = Field(
        description="Slope of anthropogenic heat vs cooling degree days",
        default_factory=DayProfile,
    )
    ah_slope_heating: DayProfile = Field(
        description="Slope of anthropogenic heat vs heating degree days",
        default_factory=DayProfile,
    )
    ahprof_24hr: HourlyProfile = Field(
        description="24-hour profile of anthropogenic heat flux",
        default_factory=HourlyProfile,
    )
    popdensdaytime: DayProfile = Field(
        description="Daytime population density", default_factory=DayProfile
    )
    popdensnighttime: float = Field(
        default=10.0, description="Nighttime population density"
    )
    popprof_24hr: HourlyProfile = Field(
        description="24-hour profile of population density",
        default_factory=HourlyProfile,
    )

    ref: Optional[Reference] = None

    # DayProfile coulmns need to be fixed
    def to_df_state(self, grid_id: int) -> pd.DataFrame:
        """
        Convert anthropogenic heat parameters to DataFrame state format.

        Args:
            grid_id (int): Grid ID for the DataFrame index.

        Returns:
            pd.DataFrame: DataFrame containing anthropogenic heat parameters.
        """

        df_state = init_df_state(grid_id)

        day_profiles = {
            "qf0_beu": self.qf0_beu,
            "qf_a": self.qf_a,
            "qf_b": self.qf_b,
            "qf_c": self.qf_c,
            "baset_cooling": self.baset_cooling,
            "baset_heating": self.baset_heating,
            "ah_min": self.ah_min,
            "ah_slope_cooling": self.ah_slope_cooling,
            "ah_slope_heating": self.ah_slope_heating,
            "popdensdaytime": self.popdensdaytime,
        }
        for param_name, profile in day_profiles.items():
            df_day_profile = profile.to_df_state(grid_id, param_name)
            df_state = df_state.combine_first(df_day_profile)

        hourly_profiles = {
            "ahprof_24hr": self.ahprof_24hr,
            "popprof_24hr": self.popprof_24hr,
        }
        for param_name, profile in hourly_profiles.items():
            df_hourly_profile = profile.to_df_state(grid_id, param_name)
            df_state = df_state.combine_first(df_hourly_profile)

        df_state.loc[grid_id, ("popdensnighttime", "0")] = self.popdensnighttime

        return df_state

    @classmethod
    def from_df_state(cls, df: pd.DataFrame, grid_id: int) -> "AnthropogenicHeat":
        """
        Reconstruct AnthropogenicHeat from a DataFrame state format.

        Args:
            df (pd.DataFrame): DataFrame containing anthropogenic heat parameters.
            grid_id (int): Grid ID for the DataFrame index.

        Returns:
            AnthropogenicHeat: Instance of AnthropogenicHeat.
        """

        # Extract DayProfile attributes
        day_profiles = {
            "qf0_beu": DayProfile.from_df_state(df, grid_id, "qf0_beu"),
            "qf_a": DayProfile.from_df_state(df, grid_id, "qf_a"),
            "qf_b": DayProfile.from_df_state(df, grid_id, "qf_b"),
            "qf_c": DayProfile.from_df_state(df, grid_id, "qf_c"),
            "baset_cooling": DayProfile.from_df_state(df, grid_id, "baset_cooling"),
            "baset_heating": DayProfile.from_df_state(df, grid_id, "baset_heating"),
            "ah_min": DayProfile.from_df_state(df, grid_id, "ah_min"),
            "ah_slope_cooling": DayProfile.from_df_state(
                df, grid_id, "ah_slope_cooling"
            ),
            "ah_slope_heating": DayProfile.from_df_state(
                df, grid_id, "ah_slope_heating"
            ),
            "popdensdaytime": DayProfile.from_df_state(df, grid_id, "popdensdaytime"),
        }

        # Extract HourlyProfile attributes
        hourly_profiles = {
            "ahprof_24hr": HourlyProfile.from_df_state(df, grid_id, "ahprof_24hr"),
            "popprof_24hr": HourlyProfile.from_df_state(df, grid_id, "popprof_24hr"),
        }

        # Extract scalar attribute
        popdensnighttime = df.loc[grid_id, ("popdensnighttime", "0")]

        # Construct and return AnthropogenicHeat instance
        return cls(
            **day_profiles,
            **hourly_profiles,
            popdensnighttime=popdensnighttime,
        )


class CO2Params(BaseModel): # TODO: May need to add the ValueWithDOI to the profiles here
    co2pointsource: ValueWithDOI[float] = Field(
        default=ValueWithDOI(0.0), description="CO2 point source emission factor"
    )
    ef_umolco2perj: ValueWithDOI[float] = Field(
        default=ValueWithDOI(0.0), description="CO2 emission factor per unit of fuel"
    )
    enef_v_jkm: ValueWithDOI[float] = Field(
        default=ValueWithDOI(0.0), description="CO2 emission factor per unit of vehicle distance"
    )
    fcef_v_kgkm: DayProfile = Field(
        description="Fuel consumption efficiency for vehicles",
        default_factory=DayProfile,
    )
    frfossilfuel_heat: ValueWithDOI[float] = Field(
        default=ValueWithDOI(0.0), description="Fraction of fossil fuel heat"
    )
    frfossilfuel_nonheat: ValueWithDOI[float] = Field(
        default=ValueWithDOI(0.0), description="Fraction of fossil fuel non-heat"
    )
    maxfcmetab: ValueWithDOI[float] = Field(
        default=ValueWithDOI(0.0), description="Maximum fuel consumption metabolic rate"
    )
    maxqfmetab: ValueWithDOI[float] = Field(
        default=ValueWithDOI(0.0), description="Maximum heat production metabolic rate"
    )
    minfcmetab: ValueWithDOI[float] = Field(
        default=ValueWithDOI(0.0), description="Minimum fuel consumption metabolic rate"
    )
    minqfmetab: ValueWithDOI[float] = Field(
        default=ValueWithDOI(0.0), description="Minimum heat production metabolic rate"
    )
    trafficrate: DayProfile = Field(
        description="Traffic rate", default_factory=DayProfile
    )
    trafficunits: ValueWithDOI[float] = Field(default=ValueWithDOI(0.0), description="Traffic units")
    traffprof_24hr: HourlyProfile = Field(
        description="24-hour profile of traffic rate", default_factory=HourlyProfile
    )
    humactivity_24hr: HourlyProfile = Field(
        description="24-hour profile of human activity", default_factory=HourlyProfile
    )

    ref: Optional[Reference] = None

    # DayProfile coulmns need to be fixed
    def to_df_state(self, grid_id: int) -> pd.DataFrame:
        """
        Convert CO2 parameters to DataFrame state format.

        Args:
            grid_id (int): Grid ID for the DataFrame index.

        Returns:
            pd.DataFrame: DataFrame containing CO2 parameters.
        """

        df_state = init_df_state(grid_id)

        scalar_params = {
            "co2pointsource": self.co2pointsource.value,
            "ef_umolco2perj": self.ef_umolco2perj.value,
            "enef_v_jkm": self.enef_v_jkm.value,
            "frfossilfuel_heat": self.frfossilfuel_heat.value,
            "frfossilfuel_nonheat": self.frfossilfuel_nonheat.value,
            "maxfcmetab": self.maxfcmetab.value,
            "maxqfmetab": self.maxqfmetab.value,
            "minfcmetab": self.minfcmetab.value,
            "minqfmetab": self.minqfmetab.value,
            "trafficunits": self.trafficunits.value,
        }
        for param_name, value in scalar_params.items():
            df_state.loc[grid_id, (param_name, "0")] = value

        day_profiles = {
            "fcef_v_kgkm": self.fcef_v_kgkm,
            "trafficrate": self.trafficrate,
        }
        for param_name, profile in day_profiles.items():
            df_day_profile = profile.to_df_state(grid_id, param_name)
            df_state = df_state.combine_first(df_day_profile)

        hourly_profiles = {
            "traffprof_24hr": self.traffprof_24hr,
            "humactivity_24hr": self.humactivity_24hr,
        }
        for param_name, profile in hourly_profiles.items():
            df_hourly_profile = profile.to_df_state(grid_id, param_name)
            df_state = df_state.combine_first(df_hourly_profile)

        return df_state

    @classmethod
    def from_df_state(cls, df: pd.DataFrame, grid_id: int) -> "CO2Params":
        """
        Reconstruct CO2Params from a DataFrame state format.

        Args:
            df (pd.DataFrame): DataFrame containing CO2 parameters.
            grid_id (int): Grid ID for the DataFrame index.

        Returns:
            CO2Params: Instance of CO2Params.
        """

        # Extract scalar attributes
        scalar_params = {
            "co2pointsource": df.loc[grid_id, ("co2pointsource", "0")],
            "ef_umolco2perj": df.loc[grid_id, ("ef_umolco2perj", "0")],
            "enef_v_jkm": df.loc[grid_id, ("enef_v_jkm", "0")],
            "frfossilfuel_heat": df.loc[grid_id, ("frfossilfuel_heat", "0")],
            "frfossilfuel_nonheat": df.loc[grid_id, ("frfossilfuel_nonheat", "0")],
            "maxfcmetab": df.loc[grid_id, ("maxfcmetab", "0")],
            "maxqfmetab": df.loc[grid_id, ("maxqfmetab", "0")],
            "minfcmetab": df.loc[grid_id, ("minfcmetab", "0")],
            "minqfmetab": df.loc[grid_id, ("minqfmetab", "0")],
            "trafficunits": df.loc[grid_id, ("trafficunits", "0")],
        }

        # Convert scalar attributes to ValueWithDOI
        scalar_params = {key: ValueWithDOI(value) for key, value in scalar_params.items()}

        # Extract DayProfile attributes
        day_profiles = {
            "fcef_v_kgkm": DayProfile.from_df_state(df, grid_id, "fcef_v_kgkm"),
            "trafficrate": DayProfile.from_df_state(df, grid_id, "trafficrate"),
        }

        # Extract HourlyProfile attributes
        hourly_profiles = {
            "traffprof_24hr": HourlyProfile.from_df_state(
                df, grid_id, "traffprof_24hr"
            ),
            "humactivity_24hr": HourlyProfile.from_df_state(
                df, grid_id, "humactivity_24hr"
            ),
        }

        # Construct and return CO2Params instance
        return cls(
            **scalar_params,
            **day_profiles,
            **hourly_profiles,
        )


class AnthropogenicEmissions(BaseModel):
    startdls: ValueWithDOI[float] = Field(
        default=ValueWithDOI(0.0), description="Start of daylight savings time in decimal day of year"
    )
    enddls: ValueWithDOI[float] = Field(
        default=ValueWithDOI(0.0), description="End of daylight savings time in decimal day of year"
    )
    heat: AnthropogenicHeat = Field(
        description="Anthropogenic heat emission parameters",
        default_factory=AnthropogenicHeat,
    )
    co2: CO2Params = Field(
        description="CO2 emission parameters", default_factory=CO2Params
    )

    ref: Optional[Reference] = None

    def to_df_state(self, grid_id: int) -> pd.DataFrame:
        """
        Convert anthropogenic emissions parameters to DataFrame state format.

        Args:
            grid_id (int): Grid ID for the DataFrame index.

        Returns:
            pd.DataFrame: DataFrame containing anthropogenic emissions parameters.
        """
        df_state = init_df_state(grid_id)

        # Set start and end daylight saving times
        df_state.loc[grid_id, ("startdls", "0")] = self.startdls.value
        df_state.loc[grid_id, ("enddls", "0")] = self.enddls.value

        # Add heat parameters
        df_heat = self.heat.to_df_state(grid_id)
        df_state = pd.concat([df_state, df_heat], axis=1)

        # Add CO2 parameters
        df_co2 = self.co2.to_df_state(grid_id)
        df_state = pd.concat([df_state, df_co2], axis=1)

        # Drop duplicate columns if necessary
        df_state = df_state.loc[:, ~df_state.columns.duplicated()]

        return df_state

    @classmethod
    def from_df_state(cls, df: pd.DataFrame, grid_id: int) -> "AnthropogenicEmissions":
        """
        Reconstruct AnthropogenicEmissions from a DataFrame state format.

        Args:
            df (pd.DataFrame): DataFrame containing anthropogenic emissions parameters.
            grid_id (int): Grid ID for the DataFrame index.

        Returns:
            AnthropogenicEmissions: Instance of AnthropogenicEmissions.
        """
        startdls = ValueWithDOI(df.loc[grid_id, ("startdls", "0")])
        enddls = ValueWithDOI(df.loc[grid_id, ("enddls", "0")])

        # Reconstruct heat parameters
        heat = AnthropogenicHeat.from_df_state(df, grid_id)

        # Reconstruct CO2 parameters
        co2 = CO2Params.from_df_state(df, grid_id)

        return cls(startdls=startdls, enddls=enddls, heat=heat, co2=co2)


class Conductance(BaseModel):
    g_max: ValueWithDOI[float] = Field(default=ValueWithDOI(40.0), description="Maximum conductance")
    g_k: ValueWithDOI[float] = Field(
        default=ValueWithDOI(0.6),
        description="Conductance parameter related to incoming solar radiation",
    )
    g_q_base: ValueWithDOI[float] = Field(
        default=ValueWithDOI(0.03),
        description="Base value for conductance parameter related to vapor pressure deficit",
    )
    g_q_shape: ValueWithDOI[float] = Field(
        default=ValueWithDOI(0.9),
        description="Shape parameter for conductance related to vapor pressure deficit",
    )
    g_t: ValueWithDOI[float] = Field(
        default=ValueWithDOI(30.0), description="Conductance parameter related to air temperature"
    )
    g_sm: ValueWithDOI[float] = Field(
        default=ValueWithDOI(0.5), description="Conductance parameter related to soil moisture"
    )
    kmax: ValueWithDOI[float] = Field(
        default=ValueWithDOI(1200.0), description="Maximum incoming shortwave radiation"
    )
    gsmodel: ValueWithDOI[int] = Field(default=ValueWithDOI(1), description="Stomatal conductance model selection")
    s1: ValueWithDOI[float] = Field(default=ValueWithDOI(0.2), description="Soil moisture threshold parameter")
    s2: ValueWithDOI[float] = Field(default=ValueWithDOI(0.5), description="Soil moisture threshold parameter")
    tl: ValueWithDOI[float] = Field(default=ValueWithDOI(0.0), description="Air temperature threshold parameter")
    th: ValueWithDOI[float] = Field(default=ValueWithDOI(50.0), description="Air temperature threshold parameter")

    ref: Optional[Reference] = Reference(ref='Test ref', DOI="test doi", ID="test id")

    def to_df_state(self, grid_id: int) -> pd.DataFrame:
        """
        Convert conductance parameters to DataFrame state format.

        Args:
            grid_id (int): Grid ID for the DataFrame index.

        Returns:
            pd.DataFrame: DataFrame containing conductance parameters.
        """

        df_state = init_df_state(grid_id)

        scalar_params = {
            "g_max": self.g_max,
            "g_k": self.g_k,
            "g_q_base": self.g_q_base,
            "g_q_shape": self.g_q_shape,
            "g_t": self.g_t,
            "g_sm": self.g_sm,
            "kmax": self.kmax,
            "gsmodel": self.gsmodel,
            "s1": self.s1,
            "s2": self.s2,
            "tl": self.tl,
            "th": self.th,
        }

        for param_name, value in scalar_params.items():
            df_state.loc[grid_id, (param_name, "0")] = value.value

        return df_state

    @classmethod
    def from_df_state(cls, df: pd.DataFrame, grid_id: int) -> "Conductance":
        """
        Reconstruct Conductance from a DataFrame state format.

        Args:
            df: DataFrame containing conductance parameters
            grid_id: Grid ID for the DataFrame index

        Returns:
            Conductance: Instance of Conductance
        """
        scalar_params = {
            "g_max": df.loc[grid_id, ("g_max", "0")],
            "g_k": df.loc[grid_id, ("g_k", "0")],
            "g_q_base": df.loc[grid_id, ("g_q_base", "0")],
            "g_q_shape": df.loc[grid_id, ("g_q_shape", "0")],
            "g_t": df.loc[grid_id, ("g_t", "0")],
            "g_sm": df.loc[grid_id, ("g_sm", "0")],
            "kmax": df.loc[grid_id, ("kmax", "0")],
            "gsmodel": int(df.loc[grid_id, ("gsmodel", "0")]),
            "s1": df.loc[grid_id, ("s1", "0")],
            "s2": df.loc[grid_id, ("s2", "0")],
            "tl": df.loc[grid_id, ("tl", "0")],
            "th": df.loc[grid_id, ("th", "0")],
        }

        # Convert scalar parameters to ValueWithDOI
        scalar_params = {key: ValueWithDOI(value) for key, value in scalar_params.items()}

        return cls(**scalar_params)


class LAIPowerCoefficients(BaseModel):
    growth_lai: ValueWithDOI[float] = Field(
        default=ValueWithDOI(0.1),
        description="Power coefficient for LAI in growth equation (LAIPower[1])",
    )
    growth_gdd: ValueWithDOI[float] = Field(
        default=ValueWithDOI(0.1),
        description="Power coefficient for GDD in growth equation (LAIPower[2])",
    )
    senescence_lai: ValueWithDOI[float] = Field(
        default=ValueWithDOI(0.1),
        description="Power coefficient for LAI in senescence equation (LAIPower[3])",
    )
    senescence_sdd: ValueWithDOI[float] = Field(
        default=ValueWithDOI(0.1),
        description="Power coefficient for SDD in senescence equation (LAIPower[4])",
    )

    ref: Optional[Reference] = None

    def to_list(self) -> List[float]:
        """Convert to list format for Fortran interface"""
        return [
            self.growth_lai,
            self.growth_gdd,
            self.senescence_lai,
            self.senescence_sdd,
        ]

    def to_df_state(self, grid_id: int, veg_idx: int) -> pd.DataFrame:
        """Convert LAI power coefficients to DataFrame state format.

        Args:
            grid_id: Grid ID for the DataFrame index
            veg_idx: Vegetation index (0: EVETR, 1: DECTR, 2: GRASS)

        Returns:
            pd.DataFrame: DataFrame containing LAI power coefficients
        """
        df_state = init_df_state(grid_id)

        # Helper function to set values in DataFrame
        def set_df_value(col_name: str, indices: Tuple, value: float):
            idx_str = str(indices)
            if (col_name, idx_str) not in df_state.columns:
                # df_state[(col_name, idx_str)] = np.nan
                df_state[(col_name, idx_str)] = None
            df_state.at[grid_id, (col_name, idx_str)] = value

        # Set power coefficients in order
        for i, value in enumerate(self.to_list()):
            set_df_value("laipower", (i, veg_idx), value.value)

        return df_state

    @classmethod
    def from_df_state(
        cls, df: pd.DataFrame, grid_id: int, veg_idx: int
    ) -> "LAIPowerCoefficients":
        """
        Reconstruct LAIPowerCoefficients from DataFrame state format.

        Args:
            df: DataFrame containing LAI power coefficients
            grid_id: Grid ID for the DataFrame index
            veg_idx: Vegetation index (0: EVETR, 1: DECTR, 2: GRASS)

        Returns:
            LAIPowerCoefficients: Instance of LAIPowerCoefficients
        """
        # Map each coefficient to its corresponding index
        coefficients = [
            ValueWithDOI(df.loc[grid_id, ("laipower", f"(0, {veg_idx})")]),
            ValueWithDOI(df.loc[grid_id, ("laipower", f"(1, {veg_idx})")]),
            ValueWithDOI(df.loc[grid_id, ("laipower", f"(2, {veg_idx})")]),
            ValueWithDOI(df.loc[grid_id, ("laipower", f"(3, {veg_idx})")]),
        ]

        # Return the instance with coefficients
        return cls(
            growth_lai=coefficients[0],
            growth_gdd=coefficients[1],
            senescence_lai=coefficients[2],
            senescence_sdd=coefficients[3],
        )


class LAIParams(BaseModel):
    baset: ValueWithDOI[float] = Field(
        default=ValueWithDOI(10.0),
        description="Base Temperature for initiating growing degree days (GDD) for leaf growth [degC]",
    )
    gddfull: ValueWithDOI[float] = Field(
        default=ValueWithDOI(100.0),
        description="Growing degree days (GDD) needed for full capacity of LAI [degC]",
    )
    basete: ValueWithDOI[float] = Field(
        default=ValueWithDOI(10.0),
        description="Base temperature for initiating senescence degree days (SDD) for leaf off [degC]",
    )
    sddfull: ValueWithDOI[float] = Field(
        default=ValueWithDOI(100.0),
        description="Senescence degree days (SDD) needed to initiate leaf off [degC]",
    )
    laimin: ValueWithDOI[float] = Field(default=ValueWithDOI(0.1), description="Leaf-off wintertime value [m2 m-2]")
    laimax: ValueWithDOI[float] = Field(
        default=ValueWithDOI(10.0), description="Full leaf-on summertime value [m2 m-2]"
    )
    laipower: LAIPowerCoefficients = Field(
        default_factory=LAIPowerCoefficients,
        description="LAI calculation power parameters for growth and senescence",
    )
    laitype: ValueWithDOI[int] = Field(
        default=ValueWithDOI(0),
        description="LAI calculation choice (0: original, 1: new high latitude)",
    )

    ref: Optional[Reference] = None

    @model_validator(mode="after")
    def validate_lai_ranges(self) -> "LAIParams":
        if self.laimin > self.laimax:
            raise ValueError(
                f"laimin ({self.laimin})must be less than or equal to laimax ({self.laimax})."
            )
        if self.baset > self.gddfull:
            raise ValueError(
                f"baset {self.baset} must be less than gddfull ({self.gddfull})."
            )
        return self

    def to_df_state(self, grid_id: int, surf_idx: int) -> pd.DataFrame:
        """Convert LAI parameters to DataFrame state format.

        Args:
            grid_id: Grid ID for the DataFrame index
            surf_idx: Surface index for vegetation (2: EVETR, 3: DECTR, 4: GRASS)

        Returns:
            pd.DataFrame: DataFrame containing LAI parameters
        """
        df_state = init_df_state(grid_id)

        # Adjust index for vegetation surfaces (surface index - 2)
        veg_idx = surf_idx - 2

        # Helper function to set values in DataFrame
        def set_df_value(col_name: str, indices: Union[Tuple, int], value: float):
            idx_str = str(indices) if isinstance(indices, int) else str(indices)
            if (col_name, idx_str) not in df_state.columns:
                # df_state[(col_name, idx_str)] = np.nan
                df_state[(col_name, idx_str)] = None
            df_state.at[grid_id, (col_name, idx_str)] = value

        # Set basic LAI parameters
        lai_params = {
            "baset": self.baset,
            "gddfull": self.gddfull,
            "basete": self.basete,
            "sddfull": self.sddfull,
            "laimin": self.laimin,
            "laimax": self.laimax,
            "laitype": self.laitype,
        }

        for param, value in lai_params.items():
            set_df_value(param, (veg_idx,), value.value)

        # Add LAI power coefficients using the LAIPowerCoefficients to_df_state method
        if self.laipower:
            df_power = self.laipower.to_df_state(grid_id, veg_idx)
            # Merge power coefficients into main DataFrame
            for col in df_power.columns:
                if col[0] != "grid_iv":  # Skip the grid_iv column
                    df_state[col] = df_power[col]

        return df_state

    @classmethod
    def from_df_state(
        cls, df: pd.DataFrame, grid_id: int, surf_idx: int
    ) -> "LAIParams":
        """
        Reconstruct LAIParams from DataFrame state format.

        Args:
            df (pd.DataFrame): DataFrame containing LAI parameters.
            grid_id (int): Grid ID for the DataFrame index.
            surf_idx (int): Surface index for vegetation (2: EVETR, 3: DECTR, 4: GRASS).

        Returns:
            LAIParams: Instance of LAIParams.
        """
        # Adjust index for vegetation surfaces (surface index - 2)
        veg_idx = surf_idx - 2

        # Helper function to extract values from DataFrame
        def get_df_value(col_name: str, indices: Union[Tuple, int]) -> float:
            idx_str = str(indices) if isinstance(indices, int) else str(indices)
            return df.loc[grid_id, (col_name, idx_str)]

        # Extract basic LAI parameters
        lai_params = {
            "baset": get_df_value("baset", (veg_idx,)),
            "gddfull": get_df_value("gddfull", (veg_idx,)),
            "basete": get_df_value("basete", (veg_idx,)),
            "sddfull": get_df_value("sddfull", (veg_idx,)),
            "laimin": get_df_value("laimin", (veg_idx,)),
            "laimax": get_df_value("laimax", (veg_idx,)),
            "laitype": int(get_df_value("laitype", (veg_idx,))),
        }

        # Convert scalar parameters to ValueWithDOI
        lai_params = {key: ValueWithDOI(value) for key, value in lai_params.items()}

        # Extract LAI power coefficients
        laipower = LAIPowerCoefficients.from_df_state(df, grid_id, veg_idx)

        return cls(**lai_params, laipower=laipower)


class VegetatedSurfaceProperties(SurfaceProperties):
    alb_min: ValueWithDOI[float] = Field(ge=0, le=1, description="Minimum albedo", default=ValueWithDOI(0.2))
    alb_max: ValueWithDOI[float] = Field(ge=0, le=1, description="Maximum albedo", default=ValueWithDOI(0.3))
    beta_bioco2: ValueWithDOI[float] = Field(
        default=ValueWithDOI(0.6), description="Biogenic CO2 exchange coefficient"
    )
    beta_enh_bioco2: ValueWithDOI[float] = Field(
        default=ValueWithDOI(0.7), description="Enhanced biogenic CO2 exchange coefficient"
    )
    alpha_bioco2: ValueWithDOI[float] = Field(
        default=ValueWithDOI(0.8), description="Biogenic CO2 exchange coefficient"
    )
    alpha_enh_bioco2: ValueWithDOI[float] = Field(
        default=ValueWithDOI(0.9), description="Enhanced biogenic CO2 exchange coefficient"
    )
    resp_a: ValueWithDOI[float] = Field(default=ValueWithDOI(1.0), description="Respiration coefficient")
    resp_b: ValueWithDOI[float] = Field(default=ValueWithDOI(1.1), description="Respiration coefficient")
    theta_bioco2: ValueWithDOI[float] = Field(
        default=ValueWithDOI(1.2), description="Biogenic CO2 exchange coefficient"
    )
    maxconductance: ValueWithDOI[float] = Field(
        default=ValueWithDOI(0.5), description="Maximum surface conductance"
    )
    min_res_bioco2: ValueWithDOI[float] = Field(
        default=ValueWithDOI(0.1), description="Minimum respiratory biogenic CO2"
    )
    lai: LAIParams = Field(
        default_factory=LAIParams, description="Leaf area index parameters"
    )
    ie_a: ValueWithDOI[float] = Field(
        default=ValueWithDOI(0.5), description="Irrigation efficiency coefficient-automatic"
    )
    ie_m: ValueWithDOI[float] = Field(
        default=ValueWithDOI(0.6), description="Irrigation efficiency coefficient-manual"
    )

    ref: Optional[Reference] = None

    @model_validator(mode="after")
    def validate_albedo_range(self) -> "VegetatedSurfaceProperties":
        if self.alb_min > self.alb_max:
            raise ValueError(
                f"alb_min (input {self.alb_min}) must be less than or equal to alb_max (entered {self.alb_max})."
            )
        return self

    def to_df_state(self, grid_id: int) -> pd.DataFrame:
        """Convert vegetated surface properties to DataFrame state format."""
        # Get base properties
        df_state = super().to_df_state(grid_id)

        # Add vegetation-specific properties
        surf_idx = self.get_surface_index()

        # Helper function to set values in DataFrame
        def set_df_value(col_name: str, idx_str: str, value: float):
            if (col_name, idx_str) not in df_state.columns:
                # df_state[(col_name, idx_str)] = np.nan
                df_state[(col_name, idx_str)] = None
            df_state.loc[grid_id, (col_name, idx_str)] = value

        # add ordinary float properties
        for attr in [
            # "alb_min",
            # "alb_max",
            "beta_bioco2",
            "beta_enh_bioco2",
            "alpha_bioco2",
            "alpha_enh_bioco2",
            "resp_a",
            "resp_b",
            "theta_bioco2",
            "maxconductance",
            "min_res_bioco2",
            "ie_a",
            "ie_m",
        ]:
            set_df_value(attr, f"({surf_idx-2},)", getattr(self, attr).value)

        df_lai = self.lai.to_df_state(grid_id, surf_idx)
        df_state = pd.concat([df_state, df_lai], axis=1).sort_index(axis=1)

        return df_state


class EvetrProperties(VegetatedSurfaceProperties): # TODO: Move waterdist VWD here?
    faievetree: ValueWithDOI[float] = Field(
        default=ValueWithDOI(0.1), description="Frontal area index of evergreen trees"
    )
    evetreeh: ValueWithDOI[float] = Field(default=ValueWithDOI(15.0), description="Evergreen tree height")
    _surface_type: Literal[SurfaceType.EVETR] = SurfaceType.EVETR
    waterdist: WaterDistribution = Field(
        default_factory=lambda: WaterDistribution(SurfaceType.EVETR),
        description="Water distribution for evergreen trees",
    )

    ref: Optional[Reference] = None

    def to_df_state(self, grid_id: int) -> pd.DataFrame:
        """Convert evergreen tree properties to DataFrame state format."""
        # Get base properties from parent
        df_state = super().to_df_state(grid_id)
        surf_idx = self.get_surface_index()

        # Helper function to set values in DataFrame
        def set_df_value(col_name: str, value: float):
            idx_str = f"({surf_idx},)"
            if (col_name, idx_str) not in df_state.columns:
                # df_state[(col_name, idx_str)] = np.nan
                df_state[(col_name, idx_str)] = None
            df_state.loc[grid_id, (col_name, idx_str)] = value

        # Add all non-inherited properties
        list_properties = ["faievetree", "evetreeh"]
        for attr in list_properties:
            df_state.loc[grid_id, (attr, "0")] = getattr(self, attr).value

        # specific properties
        df_state.loc[grid_id, ("albmin_evetr", "0")] = self.alb_min.value
        df_state.loc[grid_id, ("albmax_evetr", "0")] = self.alb_max.value

        return df_state

    @classmethod
    def from_df_state(cls, df: pd.DataFrame, grid_id: int) -> "EvetrProperties":
        """Reconstruct evergreen tree properties from DataFrame state format."""
        surf_idx = 2
        instance = super().from_df_state(df, grid_id, surf_idx)
        return instance


class DectrProperties(VegetatedSurfaceProperties):
    faidectree: ValueWithDOI[float] = Field(
        default=ValueWithDOI(0.1), description="Frontal area index of deciduous trees"
    )
    dectreeh: ValueWithDOI[float] = Field(default=ValueWithDOI(15.0), description="Deciduous tree height")
    pormin_dec: ValueWithDOI[float] = Field(
        ge=0.1, le=0.9, default=ValueWithDOI(0.2), description="Minimum porosity"
    )  # pormin_dec cannot be less than 0.1 and greater than 0.9
    pormax_dec: ValueWithDOI[float] = Field(
        ge=0.1, le=0.9, default=ValueWithDOI(0.6), description="Maximum porosity"
    )  # pormax_dec cannot be less than 0.1 and greater than 0.9
    capmax_dec: ValueWithDOI[float] = Field(default=ValueWithDOI(100.0), description="Maximum capacity")
    capmin_dec: ValueWithDOI[float] = Field(default=ValueWithDOI(10.0), description="Minimum capacity")
    _surface_type: Literal[SurfaceType.DECTR] = SurfaceType.DECTR
    waterdist: WaterDistribution = Field(
        default_factory=lambda: WaterDistribution(SurfaceType.DECTR),
        description="Water distribution for deciduous trees",
    )

    ref: Optional[Reference] = None

    @model_validator(mode="after")
    def validate_porosity_range(self) -> "DectrProperties":
        if self.pormin_dec >= self.pormax_dec:
            raise ValueError(
                f"pormin_dec ({self.pormin_dec}) must be less than pormax_dec ({self.pormax_dec})."
            )
        return self

    def to_df_state(self, grid_id: int) -> pd.DataFrame:
        """Convert deciduous tree properties to DataFrame state format."""
        # Get base properties from parent
        df_state = super().to_df_state(grid_id)

        list_properties = [
            "faidectree",
            "dectreeh",
            "pormin_dec",
            "pormax_dec",
            "capmax_dec",
            "capmin_dec",
        ]
        # Add all non-inherited properties
        for attr in list_properties:
            df_state.loc[grid_id, (attr, "0")] = getattr(self, attr).value

        # specific properties
        df_state.loc[grid_id, ("albmin_dectr", "0")] = self.alb_min.value
        df_state.loc[grid_id, ("albmax_dectr", "0")] = self.alb_max.value

        return df_state

    @classmethod
    def from_df_state(cls, df: pd.DataFrame, grid_id: int) -> "DectrProperties":
        """Reconstruct deciduous tree properties from DataFrame state format."""
        surf_idx = 3
        instance = super().from_df_state(df, grid_id, surf_idx)
        return instance


class GrassProperties(VegetatedSurfaceProperties):
    _surface_type: Literal[SurfaceType.GRASS] = SurfaceType.GRASS
    waterdist: WaterDistribution = Field(
        default_factory=lambda: WaterDistribution(SurfaceType.GRASS),
        description="Water distribution for grass",
    )

    def to_df_state(self, grid_id: int) -> pd.DataFrame:
        """Convert grass properties to DataFrame state format."""
        # Get base properties from parent
        df_state = super().to_df_state(grid_id)

        # add specific properties
        df_state[("albmin_grass", "0")] = self.alb_min.value
        df_state[("albmax_grass", "0")] = self.alb_max.value

        return df_state

    @classmethod
    def from_df_state(cls, df: pd.DataFrame, grid_id: int) -> "GrassProperties":
        """Reconstruct grass properties from DataFrame state format."""
        surf_idx = 4
        instance = super().from_df_state(df, grid_id, surf_idx)
        return instance


class SnowParams(BaseModel):
    crwmax: ValueWithDOI[float] = Field(default=ValueWithDOI(0.1), description="Maximum water capacity of snow")
    crwmin: ValueWithDOI[float] = Field(default=ValueWithDOI(0.05), description="Minimum water capacity of snow")
    narp_emis_snow: ValueWithDOI[float] = Field(default=ValueWithDOI(0.99), description="Snow surface emissivity")
    preciplimit: ValueWithDOI[float] = Field(
        default=ValueWithDOI(2.2), description="Limit for snow vs rain precipitation"
    )
    preciplimitalb: ValueWithDOI[float] = Field(
        default=ValueWithDOI(0.1), description="Precipitation limit for albedo aging"
    )
    snowalbmax: ValueWithDOI[float] = Field(default=ValueWithDOI(0.85), description="Maximum snow albedo")
    snowalbmin: ValueWithDOI[float] = Field(default=ValueWithDOI(0.4), description="Minimum snow albedo")
    snowdensmin: ValueWithDOI[float] = Field(
        default=ValueWithDOI(100.0), description="Minimum snow density (kg m-3)"
    )
    snowdensmax: ValueWithDOI[float] = Field(
        default=ValueWithDOI(400.0), description="Maximum snow density (kg m-3)"
    )
    snowlimbldg: ValueWithDOI = Field(default=ValueWithDOI(0.1), description="Snow limit on buildings")
    snowlimpaved: ValueWithDOI = Field(default=ValueWithDOI(0.1), description="Snow limit on paved surfaces")
    snowprof_24hr: HourlyProfile = Field(
        default_factory=HourlyProfile, description="24-hour snow profile"
    )
    tau_a: ValueWithDOI[float] = Field(default=ValueWithDOI(0.018), description="Aging constant for cold snow")
    tau_f: ValueWithDOI[float] = Field(default=ValueWithDOI(0.11), description="Aging constant for melting snow")
    tau_r: ValueWithDOI[float] = Field(default=ValueWithDOI(0.05), description="Aging constant for refreezing snow")
    tempmeltfact: ValueWithDOI[float] = Field(default=ValueWithDOI(0.12), description="Temperature melt factor")
    radmeltfact: ValueWithDOI[float] = Field(default=ValueWithDOI(0.0016), description="Radiation melt factor")

    ref: Optional[Reference] = None

    @model_validator(mode="after")
    def validate_crw_range(self) -> "SnowParams":
        if self.crwmin >= self.crwmax:
            raise ValueError(
                f"crwmin ({self.crwmin}) must be less than crwmax ({self.crwmax})."
            )
        return self

    @model_validator(mode="after")
    def validate_snowalb_range(self) -> "SnowParams":
        if self.snowalbmin >= self.snowalbmax:
            raise ValueError(
                f"snowalbmin ({self.snowalbmin}) must be less than snowalbmax ({self.snowalbmax})."
            )
        return self

    def to_df_state(self, grid_id: int) -> pd.DataFrame:
        """
        Convert snow parameters to DataFrame state format.

        Args:
            grid_id (int): Grid ID for the DataFrame index.

        Returns:
            pd.DataFrame: DataFrame containing snow parameters.
        """

        df_state = init_df_state(grid_id)

        scalar_params = {
            "crwmax": self.crwmax,
            "crwmin": self.crwmin,
            "narp_emis_snow": self.narp_emis_snow,
            "preciplimit": self.preciplimit,
            "preciplimitalb": self.preciplimitalb,
            "snowalbmax": self.snowalbmax,
            "snowalbmin": self.snowalbmin,
            "snowdensmin": self.snowdensmin,
            "snowdensmax": self.snowdensmax,
            "snowlimbldg": self.snowlimbldg,
            "snowlimpaved": self.snowlimpaved,
            "tau_a": self.tau_a,
            "tau_f": self.tau_f,
            "tau_r": self.tau_r,
            "tempmeltfact": self.tempmeltfact,
            "radmeltfact": self.radmeltfact,
        }
        for param_name, value in scalar_params.items():
            df_state.loc[grid_id, (param_name, "0")] = value.value

        df_hourly_profile = self.snowprof_24hr.to_df_state(grid_id, "snowprof_24hr")
        df_state = df_state.combine_first(df_hourly_profile)

        return df_state

    @classmethod
    def from_df_state(cls, df: pd.DataFrame, grid_id: int) -> "SnowParams":
        """
        Reconstruct SnowParams from a DataFrame state format.

        Args:
            df: DataFrame containing snow parameters.
            grid_id: Grid ID for the DataFrame index.

        Returns:
            SnowParams: Instance of SnowParams.
        """
        # Extract scalar attributes
        scalar_params = {
            "crwmax": df.loc[grid_id, ("crwmax", "0")],
            "crwmin": df.loc[grid_id, ("crwmin", "0")],
            "narp_emis_snow": df.loc[grid_id, ("narp_emis_snow", "0")],
            "preciplimit": df.loc[grid_id, ("preciplimit", "0")],
            "preciplimitalb": df.loc[grid_id, ("preciplimitalb", "0")],
            "snowalbmax": df.loc[grid_id, ("snowalbmax", "0")],
            "snowalbmin": df.loc[grid_id, ("snowalbmin", "0")],
            "snowdensmin": df.loc[grid_id, ("snowdensmin", "0")],
            "snowdensmax": df.loc[grid_id, ("snowdensmax", "0")],
            "snowlimbldg": df.loc[grid_id, ("snowlimbldg", "0")],
            "snowlimpaved": df.loc[grid_id, ("snowlimpaved", "0")],
            "tau_a": df.loc[grid_id, ("tau_a", "0")],
            "tau_f": df.loc[grid_id, ("tau_f", "0")],
            "tau_r": df.loc[grid_id, ("tau_r", "0")],
            "tempmeltfact": df.loc[grid_id, ("tempmeltfact", "0")],
            "radmeltfact": df.loc[grid_id, ("radmeltfact", "0")],
        }

        # Convert scalar parameters to ValueWithDOI
        scalar_params = {key: ValueWithDOI(value) for key, value in scalar_params.items()}

        # Extract HourlyProfile
        snowprof_24hr = HourlyProfile.from_df_state(df, grid_id, "snowprof_24hr")

        # Construct and return the SnowParams instance
        return cls(snowprof_24hr=snowprof_24hr, **scalar_params)


class LandCover(BaseModel):
    paved: PavedProperties = Field(
        default_factory=PavedProperties,
        description="Properties for paved surfaces like roads and pavements",
    )
    bldgs: BldgsProperties = Field(
        default_factory=BldgsProperties,
        description="Properties for building surfaces including roofs and walls",
    )
    dectr: DectrProperties = Field(
        default_factory=DectrProperties,
        description="Properties for deciduous trees and vegetation",
    )
    evetr: EvetrProperties = Field(
        default_factory=EvetrProperties,
        description="Properties for evergreen trees and vegetation",
    )
    grass: GrassProperties = Field(
        default_factory=GrassProperties, description="Properties for grass surfaces"
    )
    bsoil: BsoilProperties = Field(
        default_factory=BsoilProperties, description="Properties for bare soil surfaces"
    )
    water: WaterProperties = Field(
        default_factory=WaterProperties,
        description="Properties for water surfaces like lakes and ponds",
    )

    ref: Optional[Reference] = None

    @model_validator(mode="after")
    def set_surface_types(self) -> "LandCover":
        # Set surface types and validate
        surface_map = {
            "paved": (self.paved, SurfaceType.PAVED),
            "bldgs": (self.bldgs, SurfaceType.BLDGS),
            "dectr": (self.dectr, SurfaceType.DECTR),
            "evetr": (self.evetr, SurfaceType.EVETR),
            "grass": (self.grass, SurfaceType.GRASS),
            "bsoil": (self.bsoil, SurfaceType.BSOIL),
            "water": (self.water, SurfaceType.WATER),
        }

        for prop, surface_type in surface_map.values():
            prop.set_surface_type(surface_type)

        return self

    def to_df_state(self, grid_id: int) -> pd.DataFrame:
        """Convert land cover to DataFrame state format"""
        # df_state = init_df_state(grid_id)

        list_df_state = []
        for lc in ["paved", "bldgs", "dectr", "evetr", "grass", "bsoil", "water"]:
            df_state = getattr(self, lc).to_df_state(grid_id)
            list_df_state.append(df_state)
        df_state = pd.concat(list_df_state, axis=1)
        return df_state

    @classmethod
    def from_df_state(cls, df: pd.DataFrame, grid_id: int) -> "LandCover":
        """Reconstruct LandCover instance from DataFrame state.

        Args:
            df: DataFrame containing land cover parameters
            grid_id: Grid ID for the DataFrame index

        Returns:
            LandCover: Reconstructed LandCover instance
        """
        # Reconstruct each surface type from the DataFrame
        params = {
            "paved": PavedProperties.from_df_state(df, grid_id),
            "bldgs": BldgsProperties.from_df_state(df, grid_id),
            "evetr": EvetrProperties.from_df_state(df, grid_id),
            "dectr": DectrProperties.from_df_state(df, grid_id),
            "grass": GrassProperties.from_df_state(df, grid_id),
            "bsoil": BsoilProperties.from_df_state(df, grid_id),
            "water": WaterProperties.from_df_state(df, grid_id),
        }

        # Return reconstructed instance
        return cls(**params)


class ArchetypeProperties(BaseModel):
    # Not used in STEBBS - DAVE only
    # BuildingCode='1'
    # BuildingClass='SampleClass'

    BuildingType: str='SampleType'
    BuildingName: str='SampleBuilding'
    BuildingCount: ValueWithDOI[int] = Field(
        default=ValueWithDOI(1), description="Number of buildings of this archetype [-]"
    )
    Occupants: ValueWithDOI[int] = Field(
        default=ValueWithDOI(1), description="Number of occupants present in building [-]"
    )

    # Not used in STEBBS - DAVE only
    # hhs0: int = Field(default=0, description="")
    # hhs1: int = Field(default=0, description="")
    # hhs2: int = Field(default=0, description="")
    # hhs3: int = Field(default=0, description="")
    # hhs4: int = Field(default=0, description="")
    # hhs5: int = Field(default=0, description="")
    # hhs6: int = Field(default=0, description="")
    # hhs7: int = Field(default=0, description="")
    # hhs8: int = Field(default=0, description="")
    # age_0_4: int = Field(default=0, description="")
    # age_5_11: int = Field(default=0, description="")
    # age_12_18: int = Field(default=0, description="")
    # age_19_64: int = Field(default=0, description="")
    # age_65plus: int = Field(default=0, description="")

    stebbs_Height: ValueWithDOI[float] = Field(
        default=ValueWithDOI(10.0),
        description="Building height [m]",
        gt=0.0,
    )
    FootprintArea: ValueWithDOI[float] = Field(
        default=ValueWithDOI(64.0),
        description="Building footprint area [m2]",
        gt=0.0,
    )
    WallExternalArea: ValueWithDOI[float] = Field(
        default=ValueWithDOI(80.0),
        description="External wall area (including window area) [m2]",
        gt=0.0,
    )
    RatioInternalVolume: ValueWithDOI[float] = Field(
        default=ValueWithDOI(0.01),
        description="Ratio of internal mass volume to total building volume [-]",
        ge=0.0, le=1.0,
    )
    WWR: ValueWithDOI[float] = Field(
        default=ValueWithDOI(0.20),
        description="window to wall ratio [-]",
        ge=0.0, le=1.0,
    )
    WallThickness: ValueWithDOI[float] = Field(
        default=ValueWithDOI(20.0),
        description="Thickness of external wall and roof (weighted) [m]",
        gt=0.0,
    )
    WallEffectiveConductivity: ValueWithDOI[float] = Field(
        default=ValueWithDOI(60.0),
        description="Effective thermal conductivity of walls and roofs (weighted) [W m-1 K-1]",
        gt=0.0,
    )
    WallDensity: ValueWithDOI[float] = Field(
        default=ValueWithDOI(1600.0),
        description="Effective density of the walls and roof (weighted) [kg m-3]",
        gt=0.0,
    )
    WallCp: ValueWithDOI[float] = Field(
        default=ValueWithDOI(850.0),
        description="Effective specific heat capacity of walls and roof (weighted) [J kg-1 K-1]",
        gt=0.0,
    )
    Wallx1: ValueWithDOI[float] = Field(
        default=ValueWithDOI(1.0),
        description="Weighting factor for heat capacity of walls and roof [-]",
        ge=0.0, le=1.0,
    )
    WallExternalEmissivity: ValueWithDOI[float] = Field(
        default=ValueWithDOI(0.9),
        description="Emissivity of the external surface of walls and roof [-]",
        ge=0.0, le=1.0,
    )
    WallInternalEmissivity: ValueWithDOI[float] = Field(
        default=ValueWithDOI(0.9),
        description="Emissivity of the internal surface of walls and roof [-]",
        ge=0.0, le=1.0,
    )
    WallTransmissivity: ValueWithDOI[float] = Field(
        default=ValueWithDOI(0.0),
        description="Transmissivity of walls and roof [-]",
        ge=0.0, le=1.0,
    )
    WallAbsorbtivity: ValueWithDOI[float] = Field(
        default=ValueWithDOI(0.8),
        description="Absorbtivity of walls and roof [-]",
        ge=0.0, le=1.0,
    )
    WallReflectivity: ValueWithDOI[float] = Field(
        default=ValueWithDOI(0.2),
        description="Reflectivity of the external surface of walls and roof [-]",
        ge=0.0, le=1.0,
    )
    FloorThickness: ValueWithDOI[float] = Field(
        default=ValueWithDOI(0.2),
        description="Thickness of ground floor [m]",
        gt=0.0,
    )
    GroundFloorEffectiveConductivity: ValueWithDOI[float] = Field(
        default=ValueWithDOI(0.15),
        description="Effective thermal conductivity of ground floor [W m-1 K-1]",
        gt=0.0,
    )
    GroundFloorDensity: ValueWithDOI[float] = Field(
        default=ValueWithDOI(500.0),
        description="Density of the ground floor [kg m-3]",
        gt=0.0,
    )
    GroundFloorCp: ValueWithDOI[float] = Field(
        default=ValueWithDOI(1500.0),
        description="Effective specific heat capacity of the ground floor [J kg-1 K-1]",
        gt=0.0,
    )
    WindowThickness: ValueWithDOI[float] = Field(
        default=ValueWithDOI(0.015),
        description="Window thickness [m]",
        gt=0.0,
    )
    WindowEffectiveConductivity: ValueWithDOI[float] = Field(
        default=ValueWithDOI(1.0),
        description="Effective thermal conductivity of windows [W m-1 K-1]",
        gt=0.0,
    )
    WindowDensity: ValueWithDOI[float] = Field(
        default=ValueWithDOI(2500.0),
        description="Effective density of the windows [kg m-3]",
        gt=0.0,
    )
    WindowCp: ValueWithDOI[float] = Field(
        default=ValueWithDOI(840.0),
        description="Effective specific heat capacity of windows [J kg-1 K-1]",
        gt=0.0,
    )
    WindowExternalEmissivity: ValueWithDOI[float] = Field(
        default=ValueWithDOI(0.90),
        description="Emissivity of the external surface of windows [-]",
        ge=0.0, le=1.0,
    )
    WindowInternalEmissivity: ValueWithDOI[float] = Field(
        default=ValueWithDOI(0.90),
        description="Emissivity of the internal surface of windows [-]",
        ge=0.0, le=1.0,
    )
    WindowTransmissivity: ValueWithDOI[float] = Field(
        default=ValueWithDOI(0.90),
        description="Transmissivity of windows [-]",
        ge=0.0, le=1.0,
    )
    WindowAbsorbtivity: ValueWithDOI[float] = Field(
        default=ValueWithDOI(0.01),
        description="Absorbtivity of windows [-]",
        ge=0.0, le=1.0,
    )
    WindowReflectivity: ValueWithDOI[float] = Field(
        default=ValueWithDOI(0.09),
        description="Reflectivity of the external surface of windows [-]",
        ge=0.0, le=1.0,
    )
    # TODO: Add defaults below here
    InternalMassDensity: ValueWithDOI[float] = Field(
        default=ValueWithDOI(0.0),
        description="Effective density of the internal mass [kg m-3]"
    )
    InternalMassCp: ValueWithDOI[float] = Field(
        default=ValueWithDOI(0.0),
        description="Specific heat capacity of internal mass [J kg-1 K-1]"
    )
    InternalMassEmissivity: ValueWithDOI[float] = Field(
        default=ValueWithDOI(0.0),
        description="Emissivity of internal mass [-]"
    )
    MaxHeatingPower: ValueWithDOI[float] = Field(
        default=ValueWithDOI(0.0),
        description="Maximum power demand of heating system [W]"
    )
    WaterTankWaterVolume: ValueWithDOI[float] = Field(
        default=ValueWithDOI(0.0),
        description="Volume of water in hot water tank [m3]"
    )
    MaximumHotWaterHeatingPower: ValueWithDOI[float] = Field(
        default=ValueWithDOI(0.0),
        description="Maximum power demand of water heating system [W]"
    )
    HeatingSetpointTemperature: ValueWithDOI[float] = Field(
        default=ValueWithDOI(0.0),
        description="Heating setpoint temperature [degC]"
    )
    CoolingSetpointTemperature: ValueWithDOI[float] = Field(
        default=ValueWithDOI(0.0),
        description="Cooling setpoint temperature [degC]"
    )

    ref: Optional[Reference] = None

    def to_df_state(self, grid_id: int) -> pd.DataFrame:
        """Convert ArchetypeProperties to DataFrame state format."""

        df_state = init_df_state(grid_id)

        # Create an empty DataFrame with MultiIndex columns
        columns = [(field.lower(), "0") for field in self.model_fields.keys() if field != "ref"]
        df_state = pd.DataFrame(
            index=[grid_id], columns=pd.MultiIndex.from_tuples(columns)
        )

        # Set the values in the DataFrame
        for field_name, field_info in self.model_fields.items():
            if field_name == "ref":
                continue
            attribute = getattr(self, field_name)
            if type(attribute) != str:
                attribute = attribute.value
            df_state.loc[grid_id, (field_name.lower(), "0")] = attribute

        return df_state

    @classmethod
    def from_df_state(cls, df: pd.DataFrame, grid_id: int) -> "ArchetypeProperties":
        """Reconstruct ArchetypeProperties from DataFrame state format."""
        # Extract the values from the DataFrame
        params = {
            field_name: df.loc[grid_id, (field_name, "0")]
            for field_name in cls.model_fields.keys() if field_name != "ref"
        }

        # Convert params to ValueWithDOI
        params = {key: ValueWithDOI(value) for key, value in params.items()}

        # Create an instance using the extracted parameters
        return cls(**params)


class StebbsProperties(BaseModel):
    WallInternalConvectionCoefficient: ValueWithDOI[float] = Field(
        default=ValueWithDOI(0.0),
        description="Internal convection coefficient of walls and roof [W m-2 K-1]",
    )
    InternalMassConvectionCoefficient: ValueWithDOI[float] = Field(
        default=ValueWithDOI(0.0), description="Convection coefficient of internal mass [W m-2 K-1]"
    )
    FloorInternalConvectionCoefficient: ValueWithDOI[float] = Field(
        default=ValueWithDOI(0.0),
        description="Internal convection coefficient of ground floor [W m-2 K-1]",
    )
    WindowInternalConvectionCoefficient: ValueWithDOI[float] = Field(
        default=ValueWithDOI(0.0),
        description="Internal convection coefficient of windows [W m-2 K-1]",
    )
    WallExternalConvectionCoefficient: ValueWithDOI[float] = Field(
        default=ValueWithDOI(0.0),
        description="Initial external convection coefficient of walls and roof [W m-2 K-1]",
    )
    WindowExternalConvectionCoefficient: ValueWithDOI[float] = Field(
        default=ValueWithDOI(0.0),
        description="Initial external convection coefficient of windows [W m-2 K-1]",
    )
    GroundDepth: ValueWithDOI[float] = Field(
        default=ValueWithDOI(0.0), description="Depth of external ground (deep soil) [m]"
    )
    ExternalGroundConductivity: ValueWithDOI[float] = Field(default=ValueWithDOI(0.0), description="")
    IndoorAirDensity: ValueWithDOI[float] = Field(
        default=ValueWithDOI(0.0), description="Density of indoor air [kg m-3]"
    )
    IndoorAirCp: ValueWithDOI[float] = Field(
        default=ValueWithDOI(0.0), description="Specific heat capacity of indoor air [J kg-1 K-1]"
    )
    WallBuildingViewFactor: ValueWithDOI[float] = Field(
        default=ValueWithDOI(0.0), description="Building view factor of external walls [-]"
    )
    WallGroundViewFactor: ValueWithDOI[float] = Field(
        default=ValueWithDOI(0.0), description="Ground view factor of external walls [-]"
    )
    WallSkyViewFactor: ValueWithDOI[float] = Field(
        default=ValueWithDOI(0.0), description="Sky view factor of external walls [-]"
    )
    MetabolicRate: ValueWithDOI[float] = Field(
        default=ValueWithDOI(0.0), description="Metabolic rate of building occupants [W]"
    )
    LatentSensibleRatio: ValueWithDOI[float] = Field(
        default=ValueWithDOI(0.0),
        description="Latent-to-sensible ratio of metabolic energy release of occupants [-]",
    )
    ApplianceRating: ValueWithDOI[float] = Field(
        default=ValueWithDOI(0.0), description="Power demand of single appliance [W]"
    )
    TotalNumberofAppliances: ValueWithDOI[float] = Field(
        default=ValueWithDOI(0.0), description="Number of appliances present in building [-]"
    )
    ApplianceUsageFactor: ValueWithDOI[float] = Field(
        default=ValueWithDOI(0.0), description="Number of appliances in use [-]"
    )
    HeatingSystemEfficiency: ValueWithDOI[float] = Field(
        default=ValueWithDOI(0.0), description="Efficiency of space heating system [-]"
    )
    MaxCoolingPower: ValueWithDOI[float] = Field(
        default=ValueWithDOI(0.0), description="Maximum power demand of cooling system [W]"
    )
    CoolingSystemCOP: ValueWithDOI[float] = Field(
        default=ValueWithDOI(0.0), description="Coefficient of performance of cooling system [-]"
    )
    VentilationRate: ValueWithDOI[float] = Field(
        default=ValueWithDOI(0.0), description="Ventilation rate (air changes per hour, ACH) [h-1]"
    )
    IndoorAirStartTemperature: ValueWithDOI[float] = Field(
        default=ValueWithDOI(0.0), description="Initial indoor air temperature [degC]"
    )
    IndoorMassStartTemperature: ValueWithDOI[float] = Field(
        default=ValueWithDOI(0.0), description="Initial indoor mass temperature [degC]"
    )
    WallIndoorSurfaceTemperature: ValueWithDOI[float] = Field(
        default=ValueWithDOI(0.0), description="Initial wall/roof indoor surface temperature [degC]"
    )
    WallOutdoorSurfaceTemperature: ValueWithDOI[float] = Field(
        default=ValueWithDOI(0.0), description="Initial wall/roof outdoor surface temperature [degC]"
    )
    WindowIndoorSurfaceTemperature: ValueWithDOI[float] = Field(
        default=ValueWithDOI(0.0), description="Initial window indoor surface temperature [degC]"
    )
    WindowOutdoorSurfaceTemperature: ValueWithDOI[float] = Field(
        default=ValueWithDOI(0.0), description="Initial window outdoor surface temperature [degC]"
    )
    GroundFloorIndoorSurfaceTemperature: ValueWithDOI[float] = Field(
        default=ValueWithDOI(0.0),
        description="Initial ground floor indoor surface temperature [degC]",
    )
    GroundFloorOutdoorSurfaceTemperature: ValueWithDOI[float] = Field(
        default=ValueWithDOI(0.0),
        description="Initial ground floor outdoor surface temperature [degC]",
    )
    WaterTankTemperature: ValueWithDOI[float] = Field(
        default=ValueWithDOI(0.0), description="Initial water temperature in hot water tank [degC]"
    )
    InternalWallWaterTankTemperature: ValueWithDOI[float] = Field(
        default=ValueWithDOI(0.0),
        description="Initial hot water tank internal wall temperature [degC]",
    )
    ExternalWallWaterTankTemperature: ValueWithDOI[float] = Field(
        default=ValueWithDOI(0.0),
        description="Initial hot water tank external wall temperature [degC]",
    )
    WaterTankWallThickness: ValueWithDOI[float] = Field(
        default=ValueWithDOI(0.0), description="Hot water tank wall thickness [m]"
    )
    MainsWaterTemperature: ValueWithDOI[float] = Field(
        default=ValueWithDOI(0.0),
        description="Temperature of water coming into the water tank [degC]",
    )
    WaterTankSurfaceArea: ValueWithDOI[float] = Field(
        default=ValueWithDOI(0.0), description="Surface area of hot water tank cylinder [m2]"
    )
    HotWaterHeatingSetpointTemperature: ValueWithDOI[float] = Field(
        default=ValueWithDOI(0.0), description="Water tank setpoint temperature [degC]"
    )
    HotWaterTankWallEmissivity: ValueWithDOI[float] = Field(
        default=ValueWithDOI(0.0),
        description="Effective external wall emissivity of the hot water tank [-]",
    )
    DomesticHotWaterTemperatureInUseInBuilding: ValueWithDOI[float] = Field(
        default=ValueWithDOI(0.0),
        description="Initial water temperature of water held in use in building [degC]",
    )
    InternalWallDHWVesselTemperature: ValueWithDOI[float] = Field(
        default=ValueWithDOI(0.0),
        description="Initial hot water vessel internal wall temperature [degC]",
    )
    ExternalWallDHWVesselTemperature: ValueWithDOI[float] = Field(
        default=ValueWithDOI(0.0),
        description="Initial hot water vessel external wall temperature [degC]",
    )
    DHWVesselWallThickness: ValueWithDOI[float] = Field(
        default=ValueWithDOI(0.0), description="Hot water vessel wall thickness [m]"
    )
    DHWWaterVolume: ValueWithDOI[float] = Field(
        default=ValueWithDOI(0.0), description="Volume of water held in use in building [m3]"
    )
    DHWSurfaceArea: ValueWithDOI[float] = Field(
        default=ValueWithDOI(0.0), description="Surface area of hot water in vessels in building [m2]"
    )
    DHWVesselEmissivity: ValueWithDOI[float] = Field(
        default=ValueWithDOI(0.0),
        description="NEEDS CHECKED! NOT USED (assumed same as DHWVesselWallEmissivity) [-]",
    )
    HotWaterFlowRate: ValueWithDOI[float] = Field(
        default=ValueWithDOI(0.0), description="Hot water flow rate from tank to vessel [m3 s-1]"
    )
    DHWDrainFlowRate: ValueWithDOI[float] = Field(
        default=ValueWithDOI(0.0),
        description="Flow rate of hot water held in building to drain [m3 s-1]",
    )
    DHWSpecificHeatCapacity: ValueWithDOI[float] = Field(
        default=ValueWithDOI(0.0), description="Specific heat capacity of hot water [J kg-1 K-1]"
    )
    HotWaterTankSpecificHeatCapacity: ValueWithDOI[float] = Field(
        default=ValueWithDOI(0.0),
        description="Specific heat capacity of hot water tank wal [J kg-1 K-1]",
    )
    DHWVesselSpecificHeatCapacity: ValueWithDOI[float] = Field(
        default=ValueWithDOI(0.0),
        description="Specific heat capacity of vessels containing hot water in use in buildings [J kg-1 K-1]",
    )
    DHWDensity: ValueWithDOI[float] = Field(
        default=ValueWithDOI(0.0), description="Density of hot water in use [kg m-3]"
    )
    HotWaterTankWallDensity: ValueWithDOI[float] = Field(
        default=ValueWithDOI(0.0), description="Density of hot water tank wall [kg m-3]"
    )
    DHWVesselDensity: ValueWithDOI[float] = Field(
        default=ValueWithDOI(0.0),
        description="Density of vessels containing hot water in use [kg m-3]",
    )
    HotWaterTankBuildingWallViewFactor: ValueWithDOI[float] = Field(
        default=ValueWithDOI(0.0),
        description="Water tank/vessel internal building wall/roof view factor [-]",
    )
    HotWaterTankInternalMassViewFactor: ValueWithDOI[float] = Field(
        default=ValueWithDOI(0.0),
        description="Water tank/vessel building internal mass view factor [-]",
    )
    HotWaterTankWallConductivity: ValueWithDOI[float] = Field(
        default=ValueWithDOI(0.0),
        description="Effective wall conductivity of the hot water tank [W m-1 K-1]",
    )
    HotWaterTankInternalWallConvectionCoefficient: ValueWithDOI[float] = Field(
        default=ValueWithDOI(0.0),
        description="Effective internal wall convection coefficient of the hot water tank [W m-2 K-1]",
    )
    HotWaterTankExternalWallConvectionCoefficient: ValueWithDOI[float] = Field(
        default=ValueWithDOI(0.0),
        description="Effective external wall convection coefficient of the hot water tank [W m-2 K-1]",
    )
    DHWVesselWallConductivity: ValueWithDOI[float] = Field(
        default=ValueWithDOI(0.0),
        description="Effective wall conductivity of the hot water tank [W m-1 K-1]",
    )
    DHWVesselInternalWallConvectionCoefficient: ValueWithDOI[float] = Field(
        default=ValueWithDOI(0.0),
        description="Effective internal wall convection coefficient of the vessels holding hot water in use in building [W m-2 K-1]",
    )
    DHWVesselExternalWallConvectionCoefficient: ValueWithDOI[float] = Field(
        default=ValueWithDOI(0.0),
        description="Effective external wall convection coefficient of the vessels holding hot water in use in building [W m-2 K-1]",
    )
    DHWVesselWallEmissivity: ValueWithDOI[float] = Field(
        default=ValueWithDOI(0.0),
        description="Effective external wall emissivity of hot water being used within building [-]",
    )
    HotWaterHeatingEfficiency: ValueWithDOI[float] = Field(
        default=ValueWithDOI(0.0), description="Efficiency of hot water system [-]"
    )
    MinimumVolumeOfDHWinUse: ValueWithDOI[float] = Field(
        default=ValueWithDOI(0.0), description="Minimum volume of hot water in use [m3]"
    )

    ref: Optional[Reference] = None

    def to_df_state(self, grid_id: int) -> pd.DataFrame:
        """Convert StebbsProperties to DataFrame state format."""
        df_state = init_df_state(grid_id)

        # Create an empty DataFrame with MultiIndex columns
        columns = [(field.lower(), "0") for field in self.model_fields.keys() if field != "ref"]
        df_state = pd.DataFrame(
            index=[grid_id], columns=pd.MultiIndex.from_tuples(columns)
        )

        # Set the values in the DataFrame
        for field_name, field_info in self.model_fields.items():
            if field_name == "ref":
                continue
            df_state.loc[grid_id, (field_name.lower(), "0")] = getattr(self, field_name).value

        return df_state

    @classmethod
    def from_df_state(cls, df: pd.DataFrame, grid_id: int) -> "StebbsProperties":
        """Reconstruct StebbsProperties from DataFrame state format."""
        # Extract the values from the DataFrame
        params = {
            field_name: df.loc[grid_id, (field_name, "0")]
            for field_name in cls.model_fields.keys() if field_name != "ref"
        }

        # Convert params to ValueWithDOI
        params = {key: ValueWithDOI(value) for key, value in params.items()}

        # Create an instance using the extracted parameters
        return cls(**params)


class SiteProperties(BaseModel):
    lat: ValueWithDOI[float] = Field(
        ge=-90, le=90, description="Latitude of the site in degrees", default=ValueWithDOI(51.5)
    )
    lng: ValueWithDOI[float] = Field(
        ge=-180, le=180, description="Longitude of the site in degrees", default=ValueWithDOI(-0.13)
    )
    alt: ValueWithDOI[float] = Field(
        gt=0, description="Altitude of the site in metres above sea level", default=ValueWithDOI(40.0)
    )
    timezone: ValueWithDOI[int] = Field(
        ge=-12, le=12, description="Time zone offset from UTC in hours", default=ValueWithDOI(0)
    )
    surfacearea: ValueWithDOI[float] = Field(
        gt=0,
        description="Total surface area of the site in square metres",
        default=ValueWithDOI(10000.0),
    )
    z: ValueWithDOI[float] = Field(gt=0, description="Measurement height in metres", default=ValueWithDOI(10.0))
    z0m_in: ValueWithDOI[float] = Field(
        gt=0, description="Momentum roughness length in metres", default=ValueWithDOI(1.0)
    )
    zdm_in: ValueWithDOI[float] = Field(
        gt=0, description="Zero-plane displacement height in metres", default=ValueWithDOI(5.0)
    )
    pipecapacity: ValueWithDOI[float] = Field(
        gt=0, description="Maximum capacity of drainage pipes in mm/hr", default=ValueWithDOI(100.0)
    )
    runofftowater: ValueWithDOI[float] = Field(
        ge=0,
        le=1,
        description="Fraction of excess water going to water bodies",
        default=ValueWithDOI(0.0),
    )
    narp_trans_site: ValueWithDOI[float] = Field(
        description="Site-specific NARP transmission coefficient", default=ValueWithDOI(0.2)
    )
    lumps: LUMPSParams = Field(
        default_factory=LUMPSParams,
        description="Parameters for Local-scale Urban Meteorological Parameterization Scheme",
    )
    spartacus: SPARTACUSParams = Field(
        default_factory=SPARTACUSParams,
        description="Parameters for Solar Parametrizations for Radiative Transfer through Urban Canopy Scheme",
    )
    stebbs: StebbsProperties = Field(
        default_factory=StebbsProperties,
        description="Parameters for the STEBBS building energy model",
    )
    building_archetype: ArchetypeProperties = Field(
        default_factory=ArchetypeProperties,
        description="Parameters for building archetypes",
    )
    conductance: Conductance = Field(
        default_factory=Conductance,
        description="Parameters for surface conductance calculations",
    )
    irrigation: IrrigationParams = Field(
        default_factory=IrrigationParams,
        description="Parameters for irrigation modelling",
    )
    anthropogenic_emissions: AnthropogenicEmissions = Field(
        default_factory=AnthropogenicEmissions,
        description="Parameters for anthropogenic heat and water emissions",
    )
    snow: SnowParams = Field(
        default_factory=SnowParams, description="Parameters for snow modelling"
    )
    land_cover: LandCover = Field(
        default_factory=LandCover,
        description="Parameters for land cover characteristics",
    )
    vertical_layers: VerticalLayers = Field(
        default_factory=VerticalLayers,
        description="Parameters for vertical layer structure",
    )

    ref: Optional[Reference] = None

    def to_df_state(self, grid_id: int) -> pd.DataFrame:
        """Convert site properties to DataFrame state format"""
        df_state = init_df_state(grid_id)

        # simple attributes
        for var in [
            "lat",
            "lng",
            "alt",
            "timezone",
            "surfacearea",
            "z",
            "z0m_in",
            "zdm_in",
            "pipecapacity",
            "runofftowater",
            "narp_trans_site",
        ]:
            df_state.loc[grid_id, (f"{var}", "0")] = getattr(self, var).value

        # complex attributes
        df_lumps = self.lumps.to_df_state(grid_id)
        df_spartacus = self.spartacus.to_df_state(grid_id)
        df_conductance = self.conductance.to_df_state(grid_id)
        df_irrigation = self.irrigation.to_df_state(grid_id)
        df_anthropogenic_emissions = self.anthropogenic_emissions.to_df_state(grid_id)
        df_snow = self.snow.to_df_state(grid_id)
        df_land_cover = self.land_cover.to_df_state(grid_id)
        df_vertical_layers = self.vertical_layers.to_df_state(grid_id)
        df_stebbs = self.stebbs.to_df_state(grid_id)
        df_building_archetype = self.building_archetype.to_df_state(grid_id)

        df_state = pd.concat(
            [
                df_state,
                df_lumps,
                df_spartacus,
                df_conductance,
                df_irrigation,
                df_anthropogenic_emissions,
                df_snow,
                df_land_cover,
                df_vertical_layers,
                df_stebbs,
                df_building_archetype,
            ],
            axis=1,
        )
        return df_state

    @classmethod
    def from_df_state(cls, df: pd.DataFrame, grid_id: int) -> "SiteProperties":
        """Reconstruct SiteProperties from DataFrame state format.

        Args:
            df: DataFrame containing site properties
            grid_id: Grid ID for the DataFrame index

        Returns:
            SiteProperties: Reconstructed instance
        """
        # Extract simple attributes
        params = {}
        for var in [
            "lat",
            "lng",
            "alt",
            "timezone",
            "surfacearea",
            "z",
            "z0m_in",
            "zdm_in",
            "pipecapacity",
            "runofftowater",
            "narp_trans_site",
        ]:
            params[var] = ValueWithDOI(df.loc[grid_id, (var, "0")])

        # Extract complex attributes
        params["lumps"] = LUMPSParams.from_df_state(df, grid_id)
        params["spartacus"] = SPARTACUSParams.from_df_state(df, grid_id)
        params["conductance"] = Conductance.from_df_state(df, grid_id)
        params["irrigation"] = IrrigationParams.from_df_state(df, grid_id)
        params["anthropogenic_emissions"] = AnthropogenicEmissions.from_df_state(
            df, grid_id
        )
        params["snow"] = SnowParams.from_df_state(df, grid_id)
        params["land_cover"] = LandCover.from_df_state(df, grid_id)
        params["vertical_layers"] = VerticalLayers.from_df_state(df, grid_id)

        return cls(**params)


class Site(BaseModel):
    name: str = Field(description="Name of the site", default="test site")
    gridiv: int = Field(
        description="Grid ID for identifying this site in multi-site simulations",
        default=1,
    )
    properties: SiteProperties = Field(
        default_factory=SiteProperties,
        description="Physical and morphological properties of the site",
    )
    initial_states: InitialStates = Field(
        default_factory=InitialStates,
        description="Initial conditions for model state variables",
    )

    def to_df_state(self, grid_id: int) -> pd.DataFrame:
        """Convert site to DataFrame state format"""
        df_state = init_df_state(grid_id)
        df_site_properties = self.properties.to_df_state(grid_id)
        df_initial_states = self.initial_states.to_df_state(grid_id)
        df_state = pd.concat([df_state, df_site_properties, df_initial_states], axis=1)
        return df_state


class Model(BaseModel):
    control: ModelControl = Field(
        default_factory=ModelControl,
        description="Model control parameters including timestep, output options, etc.",
    )
    physics: ModelPhysics = Field(
        default_factory=ModelPhysics,
        description="Model physics parameters including surface properties, coefficients, etc.",
    )

    def to_df_state(self, grid_id: int) -> pd.DataFrame:
        """Convert model to DataFrame state format"""
        df_state = init_df_state(grid_id)
        df_control = self.control.to_df_state(grid_id)
        df_physics = self.physics.to_df_state(grid_id)
        df_state = pd.concat([df_state, df_control, df_physics], axis=1)
        return df_state


class SUEWSConfig(BaseModel):
    name: str = Field(
        default="sample config", description="Name of the SUEWS configuration"
    )
    description: str = Field(
        default="this is a sample config for testing purposes ONLY - values are not realistic",
        description="Description of this SUEWS configuration",
    )
    model: Model = Field(
        default_factory=Model,
        description="Model control and physics parameters",
    )
    site: List[Site] = Field(
        default=[Site()],
        description="List of sites to simulate",
        min_items=1,
    )

    class Config:
        extra = "allow"

    ## This model_validator refers to min and max ranges for OHMCoefficients loaded from an Excel file
    # @model_validator(mode="after")
    # def validate_OHMCoeff(self) -> "SUEWSConfig":
    #     if (self.model.physics.storageheatmethod == 1 and self.model.physics.ohmincqf == 0) or (
    #         self.model.physics.storageheatmethod == 2 and self.model.physics.ohmincqf == 1
    #     ):
    #         cover_to_sheet = {
    #             "bldgs": "Building",
    #             "grass": "Vegetation",
    #             "evetr": "Vegetation",
    #             "dectr": "Vegetation",
    #             "water": "Water",
    #             "bsoil": "Soil",
    #             "paved": "Paved",
    #         }
    #         all_valid = True
    #         for cover, sheet_name in cover_to_sheet.items():
    #             land_cover = getattr(self.site[0].properties.land_cover, cover)
    #             if land_cover.sfr > 0:
    #                 for coef in ["a1", "a2", "a3"]:
    #                     coef_values = getattr(land_cover.ohm_coef, coef)
    #                     for season, value in coef_values.items():
    #                         min_value, max_value = min_max_values[sheet_name][coef]  # Get ranges
    #                         if not (min_value <= value <= max_value):
    #                             raise ValueError(
    #                                 f"{cover.capitalize()} {coef} ({season}): {value} "
    #                                 f"is out of range [{min_value}, {max_value}]"
    #                             )
    #                             all_valid = False
    #         if all_valid:
    #             print(
    #                 f"StorageHeatMethod is set to {self.model.physics.storageheatmethod} and "
    #                 f"OhmIncQf is set to {self.model.physics.ohmincqf}. All valid and checked."
    #             )
    #     return self

    def create_multi_index_columns(self, columns_file: str) -> pd.MultiIndex:
        """Create MultiIndex from df_state_columns.txt"""
        with open(columns_file, "r") as f:
            lines = f.readlines()

        tuples = []
        for line in lines:
            col_name, indices = line.strip().split(",", 1)
            str_indices = f"{indices}" if indices != "0" else "0"
            tuples.append((col_name, str_indices))

        return pd.MultiIndex.from_tuples(tuples)

    def to_df_state(self) -> pd.DataFrame:
        """Convert config to DataFrame state format"""
        list_df_site = []
        for grid_id in range(len(self.site)):
            df_site = self.site[grid_id].to_df_state(grid_id)
            df_model = self.model.to_df_state(grid_id)
            df_site = pd.concat([df_site, df_model], axis=1)
            list_df_site.append(df_site)

        df = pd.concat(list_df_site, axis=0)
        # remove duplicate columns
        df = df.loc[:, ~df.columns.duplicated()]

        # set index name
        df.index.set_names("grid", inplace=True)
        # set column names
        df.columns.set_names(["var", "ind_dim"], inplace=True)
        return df

    @classmethod
    def from_df_state(cls, df: pd.DataFrame) -> "SUEWSConfig":
        """Create config from DataFrame state format.

        Args:
            df (pd.DataFrame): DataFrame containing SUEWS configuration state.

        Returns:
            SUEWSConfig: Instance of SUEWSConfig reconstructed from DataFrame.
        """
        # Initialize with default values
        config = cls()

        # Get grid IDs from DataFrame index
        grid_ids = df.index.tolist()

        # Create list of sites
        sites = []
        for grid_id in grid_ids:
            # Create site instance
            site = Site(gridiv=grid_id)

            # Set site properties
            site_properties = SiteProperties.from_df_state(df, grid_id)
            site.properties = site_properties

            # Set initial states
            initial_states = InitialStates.from_df_state(df, grid_id)
            site.initial_states = initial_states

            sites.append(site)

        # Update config with reconstructed data
        config.site = sites

        # Reconstruct model
        model = Model()
        for grid_id in grid_ids:
            # Set model control
            model_control = ModelControl.from_df_state(df, grid_id)
            model.control = model_control

            # Set model physics
            model_physics = ModelPhysics.from_df_state(df, grid_id)
            model.physics = model_physics
            break  # Only need one as model is shared across sites

        config.model = model

        return config

