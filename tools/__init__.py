"""Agrega todas las tools del agente en una sola lista."""
from tools.exercise_tools import TOOLS as _EXERCISE_TOOLS
from tools.goal_tools import TOOLS as _GOAL_TOOLS
from tools.reminder_tools import TOOLS as _REMINDER_TOOLS
from tools.workout_tools import TOOLS as _WORKOUT_TOOLS

TOOLS = _WORKOUT_TOOLS + _EXERCISE_TOOLS + _REMINDER_TOOLS + _GOAL_TOOLS
