print('Loading mod: predictAim')
import BigWorld
import os
import math
import VehicleGunRotator
from gui.mods.mod_mods_gui import inject
from Math import Vector3, Matrix
from Avatar import PlayerAvatar
from constants import ARENA_PERIOD
from vehicle_systems.tankStructure import TankNodeNames, TankPartNames,TankPartIndexes
from tutorial.control.battle.functional import _StaticObjectMarker3D as StaticObjectMarker3D

balls = {}
printedVehicle = {}

class ArtyBall(object):
    def __init__(self):
        self.modelDot = None
        self.modelDotVisible = True
        self.vehicleID = None
        self.vehicle = None
        self.lastSpeedValue = None
        self.isAlive = False

    def createBall(self,vehicleID):
        self.vehicleID = vehicleID
        self.vehicle = BigWorld.entity(vehicleID)
        path = os.path.join(os.getcwd(),'res_mods','mods','shared_resources','xvm','res','objects','cylinder_red_big.model')
        self.modelDot = StaticObjectMarker3D({ 'path': path }, (0, 0, 0))
        while self.modelDot._StaticObjectMarker3D__model is None:
            print('[predictAim] could not find model: %s' % path)
            path = os.path.join(os.getcwd(),'res_mods','mods','shared_resources','xvm','res','objects','cylinder_red_big.model')
            self.modelDot = StaticObjectMarker3D({ 'path': path }, (0, 0, 0))
        self.modelDot._StaticObjectMarker3D__model.scale = (0.3, 0.5, 0.3)
        self.modelDot._StaticObjectMarker3D__model.visible = False

    def clear(self):
        if self.modelDot._StaticObjectMarker3D__model:
            self.modelDot._StaticObjectMarker3D__model.visible = False
        if self.modelDot is not None:
            self.modelDot.clear()
        self.modelDot = None

    """
    traveltime = distance_to_car / bullet_nozzle_velocity
    current_speed = car.speed
    predicted_speed = car.speed + traveltime * car.acceleration
    average_speed = ( current_speed + predicted_speed ) / 2
    predicted_pos = car.pos + average_speed * traveltime
    """
    def update(self):
        global printedVehicle
        self.vehicle = BigWorld.entity(self.vehicleID)
        if self.vehicle is not None:
            if self.vehicle.health > 0 and self.vehicle.isAlive():
                self.isAlive = True
        if self.isAlive is False or self.vehicle is None or (self.vehicle is not None and self.vehicle.health <= 0):
            print('[predictAim] enemy died or does not exists')
            self.hideVisible()
            return
        if not hasattr(BigWorld.player(), 'vehicleTypeDescriptor') or not hasattr(BigWorld.player(), 'gunRotator') or (hasattr(self.vehicle,"health") and self.vehicle.health <= 0):
            print('[predictAim] player has no vehicleTypeDescriptor or gunRotator OR enemy is has no health or health is lower/same as zero')
            self.hideVisible()
            return
        if self.modelDot is not None and self.modelDot._StaticObjectMarker3D__model:
            playerVehicleID = BigWorld.player().playerVehicleID
            if playerVehicleID:
                playerVehicle = BigWorld.entity(playerVehicleID)
                playerPosition = playerVehicle.model.node("hull").position
                self.vehicle = BigWorld.entity(self.vehicleID)
                shotSpeed = BigWorld.player().vehicleTypeDescriptor.shot.speed
                distance = playerPosition.flatDistTo(self.vehicle.model.node("hull").position)
                traveltime = distance / shotSpeed
                enemyCurrentSpeed = self.vehicle.speedInfo.value
                if self.lastSpeedValue is None:
                    self.lastSpeedValue = enemyCurrentSpeed
                enemyCurrentSpeed = (enemyCurrentSpeed + self.lastSpeedValue) / 2
                centerFront = self.vehicle.model.node("hull").position

                cMin , cMax , _ = self.vehicle.getBounds(TankPartIndexes.CHASSIS)
                _ , hMax , _ = self.vehicle.getBounds(TankPartIndexes.HULL)
                hMax.y += cMax.y
                _ , tMax , _ =self.vehicle.getBounds(TankPartIndexes.TURRET)
                tMax.y += hMax.y
                cMax.y = tMax.y
                matrix = Matrix(self.vehicle.matrix)

                FRONT_RIGTH_BOTTOM = matrix.applyVector(Vector3(cMax.x , cMin.y , cMax.z )) + self.vehicle.position
                FRONT_LEFT_BOTTOM = matrix.applyVector(Vector3(cMin.x , cMin.y , cMax.z )) + self.vehicle.position
                centerFront = (FRONT_RIGTH_BOTTOM + FRONT_LEFT_BOTTOM)/2
                #print("[predictAim]: center Front pos: %s" % centerFront)
                #print("[predictAim]: hull: %s" % self.vehicle.model.node("hull").position)
                #print("[predictAim]: center Back pos: %s" % centerBack)

                travel_distance_0 = enemyCurrentSpeed[0] * traveltime
                #travel_distance_2 = enemyCurrentSpeed[2] * traveltime

                v = centerFront - self.vehicle.model.node("hull").position
                v3 = Vector3(v)
                #v3.normalise()
                predPos_test = self.vehicle.model.node("hull").position + (v3*travel_distance_0)
                tmp_veh = BigWorld.entity(self.vehicleID)
                predPos_test[1] = tmp_veh.model.node("hull").position[1]

                self.modelDot._StaticObjectMarker3D__model.position = predPos_test
                self.modelDot._StaticObjectMarker3D__model.visible = True
                #if self.vehicleID not in printedVehicle:
                    #print('  ')
                    #print('[predictAim] DATA  %s  :' % self.vehicle.typeDescriptor.name)
                    #print('[predictAim] enemyCurrentSpeed: %s'% enemyCurrentSpeed[0:3])
                    #print('[predictAim] traveltime: %s'% traveltime)
                    #print('[predictAim] oldPos: %s'% self.vehicle.model.node("hull").position)
                    #print('[predictAim] predPos: %s'% predPos)
                    #printedVehicle[self.vehicleID] = True

    def hideVisible(self):
        if self.modelDot is not None and self.modelDot._StaticObjectMarker3D__model and self.modelDot._StaticObjectMarker3D__model.visible:
            self.modelDot._StaticObjectMarker3D__model.visible = False
    
    def testCalc(ppos,tpos):
        rad = math.atan2(tpos[0]-ppos[0],tpos[2]-ppos[2])
        dist = ppos.flatDistTo(tpos)
        deg = math.degrees(rad)
        rad1 = math.radians(tpos[0])
        rad2 = math.radians(tpos[2])
        rad12 = math.asin(math.sin(rad1)*math.cos(dist/6378.1)+math.cos(rad1)*math.sin(dist/6378.1)*math.cos(rad))
        rad22 = rad2+math.atan2(math.sin(rad)*math.sin(dist/6378.1)*math.cos(rad1),math.cos(dist/6378.1)-math.sin(rad1)*math.sin(rad2))
        deg12 = math.degrees(rad12)
        deg22 = math.degrees(rad22)
        print(deg12)
        print(deg22)

@inject.hook(VehicleGunRotator.VehicleGunRotator, '_VehicleGunRotator__updateGunMarker')
@inject.log
def hookUpdateMarkerPos(func, *args):
    global balls
    func(*args)
    #playerVehicleID = BigWorld.player().playerVehicleID
    #if playerVehicleID not in balls:
    #    balls[playerVehicleID] = ArtyBall()
    #playerVehicle = BigWorld.entity(playerVehicleID)
    #if playerVehicle and hasattr(playerVehicle,"health") and balls[playerVehicleID].vehicle is None:
    #    balls[playerVehicleID].createBall()
    #if playerVehicle and hasattr(playerVehicle,"health") and balls[playerVehicleID].vehicle is not None:
    #    balls[playerVehicleID].update()
    #elif balls[playerVehicleID].vehicle is not None:
    #    balls[playerVehicleID].isAlive = False
    #    balls[playerVehicleID].hideVisible()
    


    #print('[predictAim] before 1. for')
    for vehID, desc in BigWorld.player().arena.vehicles.items():
        #print('[predictAim] team: %s | my team: %s' % (desc['team'], BigWorld.player().team))
        if BigWorld.player().team is not desc['team']:
            #print('[predictAim] vehID not in balls: %s' % (vehID not in balls))
            if vehID not in balls:
                #print('[predictAim] CREATE Class %s' % vehID)
                balls[vehID] = ArtyBall()
    #print('[predictAim] before 2.\nBalls length: %d' % len(balls))
    for vehID, ball in balls.items():
        curVehByID = BigWorld.entity(vehID)
        if curVehByID is not None and curVehByID.isAlive() and ball.vehicle is not None and curVehByID.isStarted:
            #print('[predictAim] UPDATE ball %s' % ball)
            ball.update()
        elif curVehByID is not None and curVehByID.isAlive() and ball.vehicle is None and curVehByID.isStarted:
            #print('[predictAim] CREATE ball %s' % vehID)
            ball.createBall(vehID)
        elif curVehByID is None or not hasattr(curVehByID,"health") or curVehByID.health <= 0:
            ball.isAlive = False
            ball.hideVisible()
        else:
            #print('[predictAim] CREATE Class %s' % vehID)
            balls[vehID] = ArtyBall()


#self.modelDot._StaticObjectMarker3D__model.position = self.vehicle.model.node("hull").position + self.vehicle.speedInfo.value[0:3]         
# noinspection PyProtectedMember
# -*- coding: utf-8 -*-