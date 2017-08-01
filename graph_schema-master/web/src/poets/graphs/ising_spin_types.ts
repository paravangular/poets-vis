/// <reference path="../core/core.ts" />

import * as POETS from "../core/core" 

import {tFloat,tInt,tBoolean} from "../core/core"

import assert = POETS.assert;
import TypedData = POETS.TypedData;
import TypedDataType = POETS.TypedDataType;
import EdgeType = POETS.EdgeType;
import DeviceType = POETS.DeviceType;
import GraphType = POETS.GraphType;
import TypedDataSpec = POETS.TypedDataSpec;
import GenericTypedDataSpec = POETS.GenericTypedDataSpec;
import InputPort = POETS.InputPort;
import OutputPort = POETS.OutputPort;

export class UpdateMessage
    extends TypedData
{
    static elements : TypedDataType[] = [
        tFloat("time"),
        tInt("spin")
    ];

    constructor(
        _spec_ : TypedDataSpec,
        public time : number = 0,
        public spin : number = 0
    ) {
        super("update_message", _spec_);
    };   
};

export const initEdgeType = new EdgeType("__init__");

export const updateEdgeType = new EdgeType(
    "update",
    new GenericTypedDataSpec(UpdateMessage, UpdateMessage.elements),
);


export class IsingSpinGraphProperties
    extends TypedData
{
    static elements : TypedDataType[] = [
        tFloat("endTime"),
        tInt("width"),
        tInt("height"),
        tVector("probabilities", tFloat("probability"), 10)
    ];

    constructor(
        _spec_:TypedDataSpec,
        public endTime : number = 10,
        public width : number = 0,
        public height : number = 0,
        public probabilities : float[] = []
    ) {
        super("ising_spin_properties", _spec_)
    };
};

