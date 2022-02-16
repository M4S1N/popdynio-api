from typing import List, Optional
from fastapi import FastAPI
from pydantic import BaseModel
from enum import Enum
from fastapi.middleware.cors import CORSMiddleware
from fastapi import HTTPException
from popdyn import (
    Model,
    Transition
)

origins = ["*"]
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def cut_every(list, every, formatter):
    return [formatter(val) for i, val in enumerate(list) if i % every == 0]

class SolverMethod(Enum):
    ode = 'ODE'
    gillespie = 'Gillespie'
    tauleaping = 'TauLeaping'


class TransitionRequest(BaseModel):
    source: str
    dest: str
    alpha: float
    factors: List[str]
    includes_n: bool


class ForecastRequest(BaseModel):
    ids: List[str]
    forecast_time: int
    initial_population: List[int]
    transitions: List[TransitionRequest]
    method: SolverMethod
    cut_every: Optional[int] = 1


@app.get('/')
def hello():
    return {'msg': 'Hello from popdynio-api'}


@app.post('/forecast')
def forecast(request: ForecastRequest):
    try:
        model = Model(request.ids)

        for transition in request.transitions:
            model[transition.source, transition.dest] = Transition(
                transition.alpha, *(transition.factors), N=transition.includes_n)

        if request.method == SolverMethod.ode:
            method = 'ODE'
        elif request.method == SolverMethod.tauleaping:
            method = 'TauLeaping'
        elif request.method == SolverMethod.gillespie:
            method = 'Gillespie'

        results = model.solve(
            t=request.forecast_time, initial_pop=request.initial_population, solver=method)

        time = cut_every(results['time'].tolist(), request.cut_every, lambda x: x)

        forecast = {}
        for group in request.ids:
            forecast[group] = cut_every(results[group].tolist(), request.cut_every, lambda x: format(x, '.2f'))

        return {
            'time': time,
            'forecast': forecast,
            'model_str': str(model)
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
