"""
windows/control/__init__.py
"""
from .socket_client import SocketClient
from .calibration import CalibrationHandler
from .calibration_control import CalibrationControl
from .calibration_plus import CalibrationPlus
from .table_geometry import TableGeometry
from .ball_identifier import BallIdentifier, DetectedBall
from .vision_pipeline import VisionPipeline, CompeteBall, CompeteScene
from .vision_bridge import VisionBridge, make_mock_scene
from .sim_table import SimTable, DEFAULT_TABLE, PocketSpec
from .shot_dispatcher import ShotDispatcher
from .state_machine import StateMachine
from .hmi import HMI

__all__ = [
    "SocketClient",
    "CalibrationHandler",
    "CalibrationControl",
    "CalibrationPlus",
    "TableGeometry",
    "BallIdentifier",
    "DetectedBall",
    "VisionPipeline",
    "CompeteBall",
    "CompeteScene",
    "VisionBridge",
    "make_mock_scene",
    "SimTable",
    "DEFAULT_TABLE",
    "PocketSpec",
    "ShotDispatcher",
    "StateMachine",
    "HMI",
]
