
import * as POETS from "../core/core"

import {tFloat,tInt,tBoolean} from "../core/typed_data"

import {HeatGraphProperties} from "./heat_types"
import {initEdgeType,updateEdgeType,UpdateEdgeProperties,UpdateMessage} from "./heat_types"

import assert = POETS.assert;
import TypedData = POETS.TypedData;
import EdgeType = POETS.EdgeType;
import DeviceType = POETS.DeviceType;
import GraphType = POETS.GraphType;
import TypedDataSpec = POETS.TypedDataSpec;
import GenericTypedDataSpec = POETS.GenericTypedDataSpec;
import InputPort = POETS.InputPort;
import OutputPort = POETS.OutputPort;

class Shared
{
    rng_init(x : number, y : number)
    {
        y=(x<<16)^y;
        for(unsigned i=0;i<10;i++){
            y^=(y<<13); y^=(y>>17); (y^=(y<<5));
        }
        return y;
    }


    // uint32_t urng(uint32_t &state)
    // {
    //   state = state*1664525+1013904223;
    //   return state;
    // }

    // uint32_t rng_init(uint32_t x, uint32_t y)
    // {

    // }

    // float frng(uint32_t &state)
    // { return urng(state)*2.328306400e-10f; }

    // float erng(uint32_t &state)
    // { return -log(frng(state)); }

    // void chooseNextEvent(const float *probabilities, uint32_t &rng, int32_t *spins, float *times)
    // {
    //   int sumStates=0;
    //   for(unsigned i=1; i<5; i++){ // Only sum neighbours
    //     sumStates+=spins[i];
    //   }

    //   unsigned index=(sumStates+4)/2 + 5*(spins[0]+1)/2;
    //   float prob=probabilities[index];

    //   if( frng(rng) < prob){
    //     spins[0] *= -1; // Flip
    //   }
    //   times[0] += erng(rng);
    // }

    // ]]>
}

class CellDeviceProperties
    extends TypedData
{
    static elements = [tInt("x"),tInt("y")];

    constructor(
        _spec_ : TypedDataSpec,
        public x : number = 0,
        public y : number = 0
    ){
        super("cell_properties", _spec_);
    };
};

class CellDeviceState
    extends TypedData
{
    static elements = [ tInt("rng"), tVector("spins", tInt("spin"), 5),
                        tVector("times", tFloat("time"), 5), tInt("spin"),
                        tFloat("lastFlipTime"), tInt("rts") ];

    constructor(
        _spec_ : TypedDataSpec,
        public rng : number = 0 ,
        public spins : int[] = [],
        public times : float[] = [],
        public spin : number = 0,
        public lastFlipTime : number = 0,
        public rts : number = 0
    ){
        super("cell_state", _spec_);
    };
};

class CellInitInputPort
    extends InputPort
{
    constructor()
    {
        super("__init__", initEdgeType);
    }   
    
    onReceive(
        graphPropertiesG : TypedData,
        devicePropertiesG : TypedData,
        deviceStateG : TypedData,
        edgePropertiesG : TypedData,
        edgeStateG : TypedData,
        messageG : TypedData,
        rts : { [key:string] : boolean; }
    ) : void
     {
        let deviceProperties = devicePropertiesG as CellDeviceProperties;
        let deviceState = deviceStateG as CellDeviceState;
        let graphProperties = graphPropertiesG as IsingSpinGraphProperties;
        x = deviceProperties.x;
        y = deviceProperties.y;
        W = deviceProperties.width;
        H = deviceProperties.height;


        // CRAP AHEAD
        seed = Shared.rng_init(x, y);

        deviceState.spins[1] = (Shared.urng(seed)>>31) ? +1 : -1;
        deviceState.times[1] = Shared.erng(seed);

        seed = rng_init( (x+1)%W, y );
        deviceState.spins[2] = (Shared.urng(seed)>>31) ? +1 : -1;
        deviceState.times[2] = Shared.erng(seed);

        seed = rng_init( x, (y+1)%H );
        deviceState.spins[3] = (Shared.urng(seed)>>31) ? +1 : -1;
        deviceState.times[3] = Shared.erng(seed);

        seed = rng_init( (x+W-1)%W, y );
        deviceState.spins[4] = (Shared.urng(seed)>>31) ? +1 : -1;
        deviceState.times[4] = Shared.erng(seed);

        // Final one is this node
        seed = rng_init( x, y );
        deviceState.spins[0] = (Shared.urng(seed)>>31) ? +1 : -1;
        deviceState.times[0] = Shared.erng(seed);
        deviceState.rng = seed; // Store the rng state back

        deviceState.spin = deviceState.spins[0];
        deviceState.lastFlipTime = 0; // Bit redundant

          // We now have perfect knowledge of our neighbourhood, and
          // when they are planning to fire.

      
        rts["out"] = true;
        for(unsigned i = 1; i < 5; i++){
            if(deviceState.times[0] >= deviceState.times[i]){
                  deviceState.rts = false; // We are not the earliest cell in neighbourhood
            }
        }

    }
};

class CellInInputPort
    extends InputPort
{
    constructor()
    {
        super("in", updateEdgeType);
    }
    
    onReceive(
        graphPropertiesG : TypedData,
        devicePropertiesG : TypedData,
        deviceStateG : TypedData,
        edgePropertiesG : TypedData,
        edgeStateG : TypedData,
        messageG : TypedData,
        rts : { [key:string] : boolean; }
    ){
        let deviceProperties=devicePropertiesG as CellDeviceProperties;
        let deviceState=deviceStateG as CellDeviceState;
        let edgeProperties=edgePropertiesG as UpdateEdgeProperties;
        let edgeState = edgeStateG as UpdateEdgeState;
        let message=messageG as UpdateMessage;

        //console.log("  w = "+edgeProperties.w);
        if(message.time >= deviceState.times[edgeProperties.direction]){
        deviceState.spins[edgeProperties.direction]=message.spin;
        deviceState.times[edgeProperties.direction]=message.time;

        handler_log(4, "from %d, new_time = %g, new_spin  %d", edgeProperties.direction, message.time, message.spin);
      }

      deviceState.rts = true;

      for(unsigned i=1; i<5; i++){
            if(deviceState.times[i] < deviceState.times[0]){
          handler_log(4, "  time[%d] = %g < time[0] = %g", i, deviceState.times[i], deviceState.times[0]);
          deviceState.rts = 0;
        }
      }
    }
};

class CellOutOutputPort
    extends OutputPort
{
    constructor()
    {
        super("out", updateEdgeType);
    }   
    
    onSend(
        graphPropertiesG : TypedData,
        devicePropertiesG : TypedData,
        deviceStateG : TypedData,
        messageG : TypedData,
        rts : { [key:string] : boolean; }
    ) : boolean
    {
        let graphProperties=graphPropertiesG as HeatGraphProperties;
        let deviceProperties=devicePropertiesG as CellDeviceProperties;
        let deviceState=deviceStateG as CellDeviceState;
        let message=messageG as UpdateMessage;
        
        if(deviceState.t > graphProperties.maxTime){
            rts["out"]=false;
            return false;
        }else{
            deviceState.v=deviceState.ca;
            deviceState.t += deviceProperties.dt;
            deviceState.cs = deviceState.ns;
            deviceState.ca = deviceState.na + deviceProperties.wSelf * deviceState.v;
            deviceState.ns=0;
            deviceState.na=0;

            message.t = deviceState.t;
            message.v=deviceState.v;
            
            rts["out"] = deviceState.cs == deviceProperties.nhood;
            return true;
        }
    }
};


export const cellDeviceType = new DeviceType(
    "cell",
    new GenericTypedDataSpec(CellDeviceProperties, CellDeviceProperties.elements),
    new GenericTypedDataSpec(CellDeviceState, CellDeviceState.elements),
    [
        new CellInitInputPort(),
        new CellInInputPort()
    ],
    [
        new CellOutOutputPort()
    ]
);

