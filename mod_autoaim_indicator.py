# Embedded file name: mod_autoaim_indicator
"""
EDIT budyx69 (29.09.2020)
FIXED elif instruction line 631

EDIT budyx69 (28.09.2020)
FIXED FEEDBACK_EVENT_ID LINE 899

EDIT RaJCeL (27.08.2020)
RESTORED REPAIR ON T UNDER HOTKEY. ADDED TEAM CHECK TO LINE 161

EDIT Heliomalt (02.08.2020)
CHAT_COMMANDS PART LINE 773 - 818 REMOVED

EDIT OLDSKOOL (09.12.2019)
UNDO: FIXED RELATIVE PATHS AFTER INTRODUCTION OF 32 AND 64 BIT CLIENT VERSIONS

EDIT RaJCeL (08.10.2019)
FIXED RELATIVE PATHS AFTER INTRODUCTION OF 32 AND 64 BIT CLIENT VERSIONS

EDIT OLDSKOOL (25.02.2019)
SUPPORT FOR WHEELED TANKS. MOD WILL LOCKIN MAGNETIC AIM WHEN POSSIBLE OTHERWISE USE AA+ HIGHLIGHTING

EDIT OLDSKOOL (01.05.2019)
G_APPLOADER FIXES FOR 1.5.0.0
"""
print 'Loading mod: autoaim_indicator v2018-05-30 (http://forum.worldoftanks.eu/index.php?/topic/441413-)'
import BigWorld, ResMgr, GUI, json, os, time, VehicleGunRotator, Math, CommandMapping, math, inspect, Vehicle, threading
from debug_utils import LOG_NOTE, LOG_ERROR, LOG_CURRENT_EXCEPTION
from skeletons.gui.app_loader import IAppLoader, GuiGlobalSpaceID
from helpers import dependency
from PlayerEvents import g_playerEvents
from constants import ARENA_PERIOD, ARENA_BONUS_TYPE, AIMING_MODE
from gui import g_guiResetters, g_keyEventHandlers, GUI_SETTINGS, SystemMessages
from AvatarInputHandler.control_modes import ArcadeControlMode, _TrajectoryControlMode
from collections import OrderedDict
from skeletons.gui.battle_session import IBattleSessionProvider
from gui.battle_control.battle_constants import VEHICLE_VIEW_STATE
from gui.battle_control.battle_constants import FEEDBACK_EVENT_ID
g_sessionProvider = dependency.instance(IBattleSessionProvider)
AUTOAIM_ANGLE_SNAPPING = False
config = {}
config_error = None
old_autoAim = None
old_onAutoAimVehicleLost = None
indicator = None
myEventsAttached = False
toggleKey = 0
toggleStateOn = True
enemies_alive = {}
allies_alive = {}
bw_player = None
bonusType = 0
playerVehicleID = 0
playerVehicle = None
cw_fow_mode = None
aa_delay_cb = 0
texts = {}
d = False
ammoCtrl = None
clipSize = 0
last_shortcut_used = None
devices_to_repair_with_hotkey = {}
LARGEREPAIRKIT = 1531
SMALLREPAIRKIT = 1275
MANUAL_FIRE_EXTINGUISHER = 251
last_timeLeft = -1
mods_log = None
key_CMD_CM_FREE_CAMERA = None
key_CMD_CM_LOCK_TARGET = None
key_CMD_CM_LOCK_TARGET_OFF = None
old_shoot = None
last_enemy_killed_id = None
last_enemy_killed_time = 0
spg = False
snap_on_focus = False
snap_on_focus_delay_cb = 0
howitzer = False
lock = threading.RLock()
isWheeled = None

def MYLOGLIVE(message, permanent_log = True, make_red = True):
    from messenger import MessengerEntry
    if message == '':
        return
    if permanent_log:
        LOG_NOTE(message)
    if make_red:
        message = '<font color="#FF0000">' + message + '</font>'
    MessengerEntry.g_instance.gui.addClientMessage(message)


def MYLOGLIVE_GARAGE(message, permanent_log = True, make_red = True):
    if message == '':
        return
    if permanent_log and d:
        MYLOG(message)
    msg_type = SystemMessages.SM_TYPE.Information
    if make_red:
        message = '<font color="#FF0000">' + message + '</font>'
        msg_type = SystemMessages.SM_TYPE.Warning
    try:
        SystemMessages.pushMessage(message, type=msg_type)
    except:
        pass


def MYLOG(msg, *args):
    if d:
        import datetime
        output = datetime.datetime.now().strftime('%H:%M:%S.%f')[:-3]
        if args:
            output = ' '.join(map(str, [output, msg, args]))
        else:
            output = ' '.join(map(str, [output, msg]))
        if mods_log:
            mods_log.write(output + '\n')
    LOG_NOTE(msg, *args)


def PT2STR(obj):
    return 'x=%f, y=%f, z=%f' % (obj.x, obj.y, obj.z)


def MYPPRINT(obj, name = None):
    import inspect, pprint
    if isinstance(obj, dict) or isinstance(obj, list):
        pprint.pprint(obj)
    elif isinstance(obj, Math.Vector3):
        if name is None:
            print PT2STR(obj)
        else:
            print '%s: %s' % (name, PT2STR(obj))
    elif hasattr(obj, '__call__'):
        pprint.pprint(inspect.getargspec(obj))
    else:
        pprint.pprint(inspect.getmembers(obj))
    return


def _LOG_EXECUTING_TIME(startTime, methodName, deltaTime = 0.1):
    finishTime = time.time()
    if finishTime - startTime > deltaTime:
        LOG_ERROR('Method "%s" takes %s%s' % (methodName, 'too much time ' if deltaTime > 0 else '', finishTime - startTime))


def myPe_onArenaPeriodChange(period = ARENA_PERIOD.BATTLE, *args):
    global clipSize
    global old_onAutoAimVehicleLost
    global playerVehicleID
    global key_CMD_CM_LOCK_TARGET_OFF
    global last_timeLeft
    global key_CMD_CM_FREE_CAMERA
    global myEventsAttached
    global bonusType
    global old_autoAim
    global spg
    global cw_fow_mode
    global indicator
    global ammoCtrl
    global old_shoot
    global howitzer
    global bw_player
    global playerVehicle
    global key_CMD_CM_LOCK_TARGET
    bw_player = BigWorld.player()
    if period is ARENA_PERIOD.BATTLE and hasattr(bw_player, 'team'):
        app = dependency.instance(IAppLoader).getApp()
        if app is None or hasattr(bw_player, 'playerVehicleID') == False:
            if d:
                MYLOG('g_appLoader.getDefBattleApp() is None or hasattr(bw_player, playerVehicleID)==False: waiting')
            BigWorld.callback(1, myPe_onArenaPeriodChange)
            return
        arena = bw_player.arena
        vehicles = arena.vehicles
        bonusType = arena.bonusType
        if bw_player.isVehicleAlive:
            playerVehicleID = bw_player.playerVehicleID
            if playerVehicleID:
                playerVehicle = BigWorld.entity(playerVehicleID)
            if config['addon-howitzer_distance_locker'] > 0:
                try:
                    speed = bw_player.vehicleTypeDescriptor.shot.speed
                    howitzer = speed < config['addon-howitzer_distance_locker']
                except AttributeError:
                    howitzer = False

                if howitzer:
                    AimingSystems._getDesiredShotPointUncached = new_getDesiredShotPointUncached
                    MYLOGLIVE('<font color="#00FF00">Shot distance locker enabled (%d m/s)</font>' % speed, False, False)
                else:
                    AimingSystems._getDesiredShotPointUncached = old_getDesiredShotPointUncached
                    MYLOGLIVE('Shot distance locker disabled (%d m/s)' % speed, False)
            if d:
                MYLOG('arena.bonusType = %d, playerVehicleID = %d, howitzer = %s' % (bonusType, playerVehicleID, howitzer))
            cw_fow_mode = bonusType in [ARENA_BONUS_TYPE.CLAN,
             ARENA_BONUS_TYPE.EVENT_BATTLES,
             ARENA_BONUS_TYPE.GLOBAL_MAP,
             ARENA_BONUS_TYPE.FALLOUT_CLASSIC,
             ARENA_BONUS_TYPE.FALLOUT_MULTITEAM,
             ARENA_BONUS_TYPE.EPIC_BATTLE]
            for vehicleID, desc in vehicles.items():
                if desc['isAlive'] == True:
                    if bw_player.team is desc['team']:
                        if not vehicleID == playerVehicleID:
                            allies_alive[vehicleID] = True
                        else:
                            spg = 'SPG' in desc['vehicleType'].type.tags
                    else:
                        enemies_alive[vehicleID] = True

            if d:
                MYLOG('enemies_alive (%d): %s, allies_alive (%d): %s' % (len(enemies_alive),
                 str(enemies_alive.keys()),
                 len(allies_alive),
                 str(allies_alive.keys())))
            if indicator is None:
                if config.get('enable_panel', True):
                    indicator = TextLabel(config.get('autoaim_indicator_panel', {}))
                    onChangeScreenResolution()
                if indicator or AUTOAIM_ANGLE_SNAPPING:
                    new_autoAim(None, False, True)
            if not myEventsAttached:
                if indicator or AUTOAIM_ANGLE_SNAPPING or config['time_snapping']['enabled']:
                    old_autoAim = bw_player.autoAim
                    bw_player.autoAim = new_autoAim
                    old_onAutoAimVehicleLost = bw_player.onAutoAimVehicleLost
                    bw_player.onAutoAimVehicleLost = new_onAutoAimVehicleLost
                arena.onVehicleKilled += myOnVehicleKilled
                bw_player.onVehicleEnterWorld += myOnVehicleEnterWorld
                old_shoot = bw_player.shoot
                bw_player.shoot = new_shoot
                if config['time_snapping']['enabled']:
                    g_sessionProvider.shared.feedback.onVehicleFeedbackReceived += __onVehicleFeedbackReceived
                myEventsAttached = True
            ammoCtrl = g_sessionProvider.shared.ammo
            if config['addon-auto_announce_reload']['clip_reload'] and not config['addon-auto_announce_reload']['only_with_C']:
                clipSize = ammoCtrl._AmmoController__gunSettings[0].size
            else:
                clipSize = 1
            last_timeLeft = -1
            if not config['addon-auto_announce_reload']['only_with_C']:
                ammoCtrl.onGunReloadTimeSet += onGunReloadTimeSet
            if config['addon-help_on_spot'] and g_sessionProvider.shared.vehicleState:
                g_sessionProvider.shared.vehicleState.onVehicleStateUpdated += __onVehicleStateUpdated
        else:
            cleanUp()
        cm = CommandMapping.g_instance
        key_CMD_CM_FREE_CAMERA = cm.get('CMD_CM_FREE_CAMERA')
        key_CMD_CM_LOCK_TARGET = cm.get('CMD_CM_LOCK_TARGET')
        key_CMD_CM_LOCK_TARGET_OFF = cm.get('CMD_CM_LOCK_TARGET_OFF')
    elif period is ARENA_PERIOD.AFTERBATTLE:
        cleanUp()
    return


def cleanUp():
    global snap_on_focus
    global indicator
    global old_shoot
    global old_onAutoAimVehicleLost
    global playerVehicleID
    global playerVehicle
    global myEventsAttached
    global old_autoAim
    if d:
        MYLOG('cleanUp')
    if myEventsAttached:
        if indicator or AUTOAIM_ANGLE_SNAPPING or config['time_snapping']['enabled']:
            bw_player.autoAim = old_autoAim
            old_autoAim = None
            bw_player.onAutoAimVehicleLost = old_onAutoAimVehicleLost
            old_onAutoAimVehicleLost = None
        if bw_player.arena:
            bw_player.arena.onVehicleKilled -= myOnVehicleKilled
        bw_player.onVehicleEnterWorld -= myOnVehicleEnterWorld
        bw_player.shoot = old_shoot
        old_shoot = None
        if config['time_snapping']['enabled'] and g_sessionProvider.shared.feedback:
            g_sessionProvider.shared.feedback.onVehicleFeedbackReceived -= __onVehicleFeedbackReceived
        myEventsAttached = False
    if indicator is not None:
        try:
            GUI.delRoot(indicator.window)
        except ValueError:
            pass

        indicator = None
    enemies_alive.clear()
    allies_alive.clear()
    playerVehicleID = 0
    playerVehicle = None
    texts.clear()
    if config['addon-help_on_spot'] and g_sessionProvider.shared.vehicleState:
        g_sessionProvider.shared.vehicleState.onVehicleStateUpdated -= __onVehicleStateUpdated
    if snap_on_focus:
        cancelTimeSnapping()
    return


def new_autoAim(target, magnetic = False, init = False):
    global aa_delay_cb
    if magnetic:
        old_autoAim(target)
        return
    if d:
        MYLOG('new_autoAim(%s, %s)' % (str(type(target)), str(init)))
    prevAutoAimVehicleID = 0
    snappingDelay = config.get('snappingDelay', 0.2)
    lock.acquire()
    if not init:
        try:
            prevAutoAimVehicleID = bw_player._PlayerAvatar__autoAimVehID
        except:
            LOG_CURRENT_EXCEPTION()
        finally:
            old_autoAim(target)

    autoAimVehicleID = bw_player._PlayerAvatar__autoAimVehID
    lock.release()
    enabled = autoAimVehicleID != 0
    if enabled:
        if snap_on_focus:
            cancelTimeSnapping()
        if indicator:
            if config.get('use_target_as_text', True):
                if not target:
                    target = BigWorld.entity(autoAimVehicleID)
                indicator.setText(texts.setdefault(autoAimVehicleID, target.typeDescriptor.type.shortUserString[0:config.get('max_characters', 15) - 1]))
            else:
                indicator.setText(config.get('autoaim_indicator_panel', {}).get('text', ''))
            indicator.setVisible(True)
    elif indicator and not snap_on_focus:
        indicator.setVisible(False)
    if not init and (prevAutoAimVehicleID == 0 or config.get('snap_continously', False)) and not enabled and config.get('snap_to_nearest', True):
        if isinstance(bw_player.inputHandler.ctrl, _TrajectoryControlMode):
            if d:
                MYLOG('_TrajectoryControlMode used')
            return
            if d:
                MYLOG('disable autoaim used')
        if config.get('no_snap_on_autoaim_off_E', True) and BigWorld.isKeyDown(key_CMD_CM_LOCK_TARGET_OFF):
            return
        if BigWorld.isKeyDown(key_CMD_CM_FREE_CAMERA) and snappingDelay > 0:
            if d:
                MYLOG('delaying %.2fs (key=%d)' % (snappingDelay, key_CMD_CM_FREE_CAMERA))
            if aa_delay_cb:
                BigWorld.cancelCallback(aa_delay_cb)
            aa_delay_cb = BigWorld.callback(snappingDelay, lambda : trySnapping(key_CMD_CM_FREE_CAMERA))
        else:
            BigWorld.callback(0, trySnapping)


def trySnapping(key = 0):
    global snap_on_focus
    global snap_on_focus_delay_cb
    global aa_delay_cb
    aa_delay_cb = 0
    isKeyDown = False
    if key:
        isKeyDown = BigWorld.isKeyDown(key)
    if not isKeyDown:
        lock.acquire()
        try:
            if bw_player._PlayerAvatar__autoAimVehID == 0:
                if d:
                    MYLOG('snapping')
                if AUTOAIM_ANGLE_SNAPPING:
                    new_target = findTarget(enemies_alive)
                    if new_target:
                        new_autoAim(new_target)
                elif config['time_snapping']['enabled']:
                    if snap_on_focus:
                        if config['time_snapping']['toggle']:
                            if d:
                                MYLOG('toggling time_snapping off')
                            cancelTimeSnapping()
                        else:
                            if d:
                                MYLOG('prolonging time_snapping')
                            seconds = config['time_snapping']['seconds']
                            if seconds:
                                BigWorld.cancelCallback(snap_on_focus_delay_cb)
                                snap_on_focus_delay_cb = BigWorld.callback(seconds, finishTimeSnapping)
                    elif isinstance(bw_player.inputHandler.ctrl, _TrajectoryControlMode):
                        if d:
                            MYLOG('_TrajectoryControlMode used (trySnapping)')
                    else:
                        new_target = BigWorld.target()
                        if new_target is None:
                            snap_on_focus = True
                            if indicator and config['time_snapping']['use_panel']:
                                indicator.setText(config['time_snapping']['panel_text'])
                                indicator.setVisible(True, True)
                            seconds = config['time_snapping']['seconds']
                            if seconds:
                                snap_on_focus_delay_cb = BigWorld.callback(seconds, finishTimeSnapping)
                            if howitzer:
                                lockShotDistance()
                        else:
                            if d:
                                MYLOG('target already highlighted - locking')
                            new_autoAim(new_target)
            elif d:
                MYLOG('target already acquired - no snapping')
        finally:
            lock.release()

    elif d:
        MYLOG('key still pressed - no snapping')
    return


def findTarget(vehicles_alive):
    if playerVehicle is None:
        return
    else:
        if isinstance(bw_player.inputHandler.ctrl, ArcadeControlMode):
            desiredShotPoint = bw_player.inputHandler.ctrl.camera.aimingSystem.getThirdPersonShotPoint()
        else:
            desiredShotPoint = bw_player.inputHandler.getDesiredShotPoint()
            if desiredShotPoint is None:
                if d:
                    MYLOG('No desiredShotPoint available - trying alternative')
                desiredShotPoint = bw_player.gunRotator.markerInfo[0]
        if desiredShotPoint is None:
            MYLOG('No desiredShotPoint available')
            return
        angle_new_target = None
        angle_to_target = math.radians(config.get('snapping_angle_degrees', 7.5))
        distance_new_target = None
        distance_to_target = int(config.get('useDistanceBelowM', 0))
        compensation = config.get('distanceAngleCompensation', False)
        camera = BigWorld.camera().position
        v1norm = normalize(desiredShotPoint - camera)
        try:
            player_position = playerVehicle.position
        except BigWorld.EntityIsDestroyedException:
            return

        for vehicleID in vehicles_alive.keys():
            vehicle = BigWorld.entity(vehicleID)
            if vehicle is not None:
                if distance_to_target or compensation:
                    distance = player_position.flatDistTo(vehicle.position)
                    if distance < distance_to_target:
                        distance_new_target = vehicle
                        distance_to_target = distance
                v2norm = normalize(vehicle.position - camera)
                angle = math.acos(v1norm.x * v2norm.x + v1norm.y * v2norm.y + v1norm.z * v2norm.z)
                if angle < 0:
                    angle = -angle
                if angle > math.pi:
                    angle = 2 * math.pi - angle
                if compensation:
                    if d:
                        MYLOG('distance compensation (angle = %f, distance = %f, compensated angle = %f' % (angle, distance, angle * (1.04 - (564 - distance) / 564)))
                    angle = angle * (1.04 - (564 - distance) / 564)
                if angle < angle_to_target:
                    angle_new_target = vehicle
                    angle_to_target = angle

        if angle_new_target is None and distance_new_target is not None:
            if d:
                MYLOG('new target acquired at %f meters' % distance_to_target)
            return distance_new_target
        if angle_new_target is not None:
            if d:
                MYLOG('new target acquired at %f degrees' % math.degrees(angle_to_target))
        return angle_new_target
        return


from math import sqrt as math_sqrt

def normalize(v):
    return v / math_sqrt(v.x * v.x + v.y * v.y + v.z * v.z)


def new_onAutoAimVehicleLost(lossReasonFlags, *args):
    old_onAutoAimVehicleLost(lossReasonFlags, *args)
    if indicator:
        indicator.setVisible(False)


def myOnVehicleKilled(vehicleID, *args):
    global last_enemy_killed_time
    global last_enemy_killed_id
    if vehicleID == playerVehicleID:
        if bonusType not in [ARENA_BONUS_TYPE.EVENT_BATTLES,
         ARENA_BONUS_TYPE.FALLOUT_CLASSIC,
         ARENA_BONUS_TYPE.FALLOUT_MULTITEAM,
         ARENA_BONUS_TYPE.EPIC_BATTLE]:
            cleanUp()
    else:
        try:
            del enemies_alive[vehicleID]
            last_enemy_killed_id = vehicleID
            last_enemy_killed_time = time.time()
        except KeyError:
            try:
                del allies_alive[vehicleID]
            except KeyError:
                pass


def myOnVehicleEnterWorld(vehicle):
    vehicleID = vehicle.id
    if cw_fow_mode and vehicle.isAlive() and bw_player.team is not vehicle.publicInfo['team']:
        enemies_alive[vehicleID] = True


class TextLabel(object):
    label = None
    shadow = None
    window = None
    color = '\\cFFFFFFFF;'
    visible = True
    x = 0
    y = 0
    hcentered = False
    vcentered = False
    altMode = False
    textures = None

    def __init__(self, panel_cfg):
        if panel_cfg.get('color', False):
            self.color = '\\c' + panel_cfg.get('color')[1:] + 'FF;'
        self.visible = panel_cfg.get('visible', True)
        self.x = panel_cfg.get('x', 0)
        self.y = panel_cfg.get('y', 0)
        self.hcentered = panel_cfg.get('hcentered', False)
        self.vcentered = panel_cfg.get('vcentered', False)
        background = os.path.join('scripts', 'client', 'gui', 'mods', panel_cfg.get('background')) if panel_cfg.get('background', '') else ''
        backgroundAlt = os.path.join('scripts', 'client', 'gui', 'mods', config['time_snapping']['panel_background']) if config['time_snapping']['panel_background'] else ''
        if backgroundAlt != '' and background != backgroundAlt:
            with open('.' + ResMgr.openSection('../paths.xml')['Paths'].values()[0:2][0].asString + '/' + backgroundAlt, 'r') as f:
                f.read()
        self.textures = {False: background,
         True: backgroundAlt}
        self.window = GUI.Window(self.textures[self.altMode])
        self.window.materialFX = 'BLEND'
        self.window.verticalAnchor = 'TOP'
        self.window.horizontalAnchor = 'LEFT'
        self.window.horizontalPositionMode = 'PIXEL'
        self.window.verticalPositionMode = 'PIXEL'
        self.window.heightMode = 'PIXEL'
        self.window.widthMode = 'PIXEL'
        self.window.width = panel_cfg.get('width', 186)
        self.window.height = panel_cfg.get('height', 32)
        self.autoSize = True
        GUI.addRoot(self.window)
        font = panel_cfg.get('font', 'mod_autoaim_indicator.font')
        if panel_cfg.get('dropShadow', False):
            self.shadow = GUI.Text('')
            self.installItem(self.shadow, font)
        self.label = GUI.Text('')
        self.installItem(self.label, font)
        self.setText(panel_cfg.get('text', '...'))
        self.setVisible(self.visible)

    def installItem(self, item, font):
        item.font = font
        self.window.addChild(item)
        item.verticalAnchor = 'CENTER'
        item.horizontalAnchor = 'CENTER'
        item.horizontalPositionMode = 'PIXEL'
        item.verticalPositionMode = 'PIXEL'
        item.position = (self.window.width / 2, self.window.height / 2, 1)
        item.colourFormatting = True

    def setVisible(self, flag, altMode = False):
        if self.altMode != altMode:
            textureName = self.textures[altMode]
            if textureName:
                self.window.textureName = self.textures[altMode]
            self.altMode = altMode
        flag = flag and self.visible
        self.window.visible = flag
        if self.shadow:
            self.shadow.visible = flag
        self.label.visible = flag

    def setText(self, text, color = None):
        if self.shadow:
            shadowText = text.replace('\\c60FF00FF;', '')
            self.shadow.text = '\\c000000FF;' + shadowText
        color = '\\c' + color + 'FF;' if color else self.color
        self.label.text = color + text


def onChangeScreenResolution():
    if indicator:
        sr = GUI.screenResolution()
        for panel in [indicator]:
            if panel is None:
                continue
            x = sr[0] / 2 - panel.window.width / 2 + panel.x if panel.hcentered else panel.x
            y = sr[1] / 2 - panel.window.height / 2 + panel.y if panel.vcentered else panel.y
            panel.window.position = (x, y, 1)

    return


def myHandleKeyEvent(event):
    global toggleStateOn
    if GUI_SETTINGS.minimapSize:
        if event.isKeyDown():
            key = event.key
            if key == toggleKey:
                if toggleStateOn:
                    toggleStateOn = False
                    g_playerEvents.onArenaPeriodChange -= myPe_onArenaPeriodChange
                    cleanUp()
                    MYLOGLIVE(config.get('toggledOffMsg', ''), make_red=False)
                else:
                    toggleStateOn = True
                    g_playerEvents.onArenaPeriodChange += myPe_onArenaPeriodChange
                    app = dependency.instance(IAppLoader).getApp()
                    if app is not None:
                        myPe_onArenaPeriodChange()
                    MYLOGLIVE(config.get('toggledOnMsg', ''), make_red=False)
                config['toggleStateOn'] = toggleStateOn
                with open(conf_file, 'w') as data_file:
                    try:
                        json.dump(config, data_file, sort_keys=True, indent=4, separators=(',', ': '))
                    except:
                        print 'Error while saving %s: %s' % (conf_file, sys.exc_info()[0])

            elif key == config['addon-repair_with_hotkey']['hotkey']:
                if config['addon-repair_with_hotkey']['use_extinguisher']:
                    if g_sessionProvider.shared.vehicleState.getStateValue(VEHICLE_VIEW_STATE.FIRE):
                        equipmentsCtrl = g_sessionProvider.shared.equipments
                        if equipmentsCtrl.canActivate(MANUAL_FIRE_EXTINGUISHER)[0]:
                            bw_player.base.vehicle_changeSetting(VEHICLE_SETTING.ACTIVATE_EQUIPMENT, equipmentsCtrl.getActivationCode(MANUAL_FIRE_EXTINGUISHER, None, bw_player))
                            return
                if devices_to_repair_with_hotkey and checkForRepairs() == True:
                    return
    return


def myHandleRepairKeyEvent(event):
    if GUI_SETTINGS.minimapSize:
        if event.isKeyDown():
            if event.key == config['addon-repair_with_hotkey']['hotkey']:
                if config['addon-repair_with_hotkey']['use_extinguisher']:
                    if g_sessionProvider.shared.vehicleState.getStateValue(VEHICLE_VIEW_STATE.FIRE):
                        equipmentsCtrl = g_sessionProvider.shared.equipments
                        if equipmentsCtrl.canActivate(MANUAL_FIRE_EXTINGUISHER)[0]:
                            bw_player.base.vehicle_changeSetting(VEHICLE_SETTING.ACTIVATE_EQUIPMENT, equipmentsCtrl.getActivationCode(MANUAL_FIRE_EXTINGUISHER, None, bw_player))
                            return
                if devices_to_repair_with_hotkey and checkForRepairs() == True:
                    return
    return


def getJson(path):
    result = None
    error = None
    js = None
    if os.path.exists(path):
        comment = False
        ljson = open(path, 'r')
        lines = ljson.readlines()
        ljson.close()
        fjson = []
        for v, i in enumerate(lines):
            a = i.replace('\t', ' ').split(' //')[0]
            if i.replace('\t', ' ').strip().startswith('/*'):
                comment = True
            if i.replace('\t', ' ').strip().endswith('*/'):
                comment = False
            if len(a.strip()) > 0 and not a.startswith('//') and not comment:
                fjson.append(a.strip())

        js = ''.join(fjson)
        try:
            result = json.loads(js)
        except ValueError as e:
            result = {}
            ErrorJSONpart = '[...] %s >>> %s <<< %s [...]' % (e.doc[e.pos - 30:e.pos], e.doc[e.pos:e.pos + 1], e.doc[e.pos + 1:e.pos + 30])
            error = 'Error with config file "%s".\n%s:\n%s' % (path.split('/')[-1], e.msg, ErrorJSONpart)

    else:
        error = 'Cannot find config file "%s".' % path.split('/')[-1]
    return (result, error, js)


conf_file = 'res_mods/mod_autoaim_indicator.json'
if not os.path.isfile(conf_file):
    conf_file = 'res_mods/configs/mod_autoaim_indicator.json'
    if not os.path.isfile(conf_file):
        conf_file = ResMgr.openSection('../paths.xml')['Paths'].values()[0:2][0].asString + '/scripts/client/gui/mods/mod_autoaim_indicator.json'
if os.path.isfile(conf_file):
    config, error, source = getJson(conf_file)
    if error != None:
        LOG_ERROR('Error while loading %s: %s' % (conf_file, error))
    config.setdefault('addon-auto_announce_reload', {'enabled': False})
    config['addon-auto_announce_reload'].setdefault('enabled', False)
    if config['addon-auto_announce_reload'].get('enabled', False):
        config['addon-auto_announce_reload'].setdefault('clip_reload', False)
        config['addon-auto_announce_reload'].setdefault('reload_longer_than', 0)
        config['addon-auto_announce_reload'].setdefault('only_with_C', False)
        config['addon-auto_announce_reload'].setdefault('clip_reload_with_double_C', False)
        config['addon-auto_announce_reload'].setdefault('second_C_timeout', 0.25)
    config.setdefault('addon-repair_with_hotkey', {})
    config['addon-repair_with_hotkey'].setdefault('enabled', False)
    config['addon-repair_with_hotkey'].setdefault('use_extinguisher', False)
    if config['addon-repair_with_hotkey'].get('enabled', True):
        config_ordered = json.loads(source, object_pairs_hook=OrderedDict)
        devices_to_repair_with_hotkey = config_ordered.get('addon-repair_with_hotkey', {}).get('devices', {})
    config.setdefault('addon-help_on_spot', False)
    config.setdefault('time_snapping', {'enabled': False})
    config['time_snapping'].setdefault('enabled', False)
    if config['time_snapping'].get('enabled', False):
        config['time_snapping'].setdefault('seconds', 2.5)
        config['time_snapping'].setdefault('toggle', False)
        config['time_snapping'].setdefault('use_panel', True)
        config['time_snapping'].setdefault('panel_text', '<AA>')
        config['time_snapping'].setdefault('panel_background', '')
        config['time_snapping'].setdefault('lock_on_pressed', True)
    config.setdefault('addon-howitzer_distance_locker', 0)
else:
    config_error = 'autoaim_indicator mod: configuration file missing - running on default values'
toggleKey = config.get('toggleKeyCode', 0)
d = config.get('debug', False)
if toggleKey > 0:
    if d:
        MYLOG('g_keyEventHandlers.add(myHandleKeyEvent)')
    g_keyEventHandlers.add(myHandleKeyEvent)
    toggleStateOn = config.get('toggleStateOn', True)
g_keyEventHandlers.add(myHandleRepairKeyEvent)
if toggleStateOn:
    g_playerEvents.onArenaPeriodChange += myPe_onArenaPeriodChange
    g_guiResetters.add(onChangeScreenResolution)

def myOnAccountBecomePlayer(*args):
    if config_error:
        MYLOGLIVE_GARAGE(config_error)


def myOnAvatarBecomeNonPlayer(*args):
    cleanUp()


g_playerEvents.onAccountBecomePlayer += myOnAccountBecomePlayer
g_playerEvents.onAvatarBecomeNonPlayer += myOnAvatarBecomeNonPlayer
config.setdefault('attack_snapping', True)
config.setdefault('follow_me_snapping', True)
if devices_to_repair_with_hotkey:
    from gui.battle_control.battle_constants import VEHICLE_DEVICE_IN_COMPLEX_ITEM, DEVICE_STATE_AS_DAMAGE
    from constants import VEHICLE_SETTING

def checkForRepairs():
    if d:
        MYLOG('checkForRepairs')
    other_devices = config['addon-repair_with_hotkey'].get('other_forcing_large_kit', {})
    to_repair = []
    other_found = False
    for deviceName, stateName in bw_player.deviceStates.iteritems():
        if stateName in DEVICE_STATE_AS_DAMAGE:
            if d:
                MYLOG('%s is %s' % (deviceName, stateName))
            repairable_states = devices_to_repair_with_hotkey.get(deviceName, [])
            if repairable_states and stateName in repairable_states:
                to_repair.append(deviceName)
                continue
            repairable_states = other_devices.get(deviceName, [])
            if repairable_states and stateName in repairable_states:
                other_found = True

    if to_repair:
        equipmentsCtrl = g_sessionProvider.shared.equipments
        if 'leftTrack' in to_repair and 'rightTrack' in to_repair:
            to_repair.remove('rightTrack')
        if (len(to_repair) > 1 or to_repair and other_found) and equipmentsCtrl.canActivate(LARGEREPAIRKIT)[0] and config['addon-repair_with_hotkey'].get('use_large_kit_when_two_damaged', True):
            if d:
                MYLOG('Using large kit for %s (other found = %s)' % (', '.join(to_repair), other_found))
            bw_player.base.vehicle_changeSetting(VEHICLE_SETTING.ACTIVATE_EQUIPMENT, equipmentsCtrl.getActivationCode(LARGEREPAIRKIT, None, bw_player))
            return True
        deviceName = None
        for deviceName in devices_to_repair_with_hotkey.keys():
            if deviceName in to_repair:
                break

        res = equipmentsCtrl.canActivate(SMALLREPAIRKIT, deviceName)
        if d:
            MYLOG('canActivate SMALLREPAIRKIT for %s? %s' % (deviceName, res[0]))
        if res[0]:
            if d:
                MYLOG('Using small kit for %s' % deviceName)
            bw_player.base.vehicle_changeSetting(VEHICLE_SETTING.ACTIVATE_EQUIPMENT, equipmentsCtrl.getActivationCode(SMALLREPAIRKIT, deviceName, bw_player))
            return True
        res = equipmentsCtrl.canActivate(LARGEREPAIRKIT)
        if d:
            MYLOG('canActivate LARGEREPAIRKIT? %s' % res[0])
        if res[0]:
            if d:
                MYLOG('Using large kit for %s' % deviceName)
            bw_player.base.vehicle_changeSetting(VEHICLE_SETTING.ACTIVATE_EQUIPMENT, equipmentsCtrl.getActivationCode(LARGEREPAIRKIT, None, bw_player))
            return True
    return False


def onGunReloadTimeSet(currShellCD, state):
    global last_timeLeft
    timeLeft = state.getTimeLeft()
    baseTime = state.getBaseValue()
    if timeLeft > 0:
        totalShots, shotsInClip = ammoCtrl.getCurrentShells()
        if d:
            MYLOG('onGunReloadTimeSet(timeLeft=%.2f, totalShots=%d, shotsInClip=%d, clipSize=%d' % (timeLeft,
             totalShots,
             shotsInClip,
             clipSize))
        if config['addon-auto_announce_reload']['clip_reload'] and clipSize > 1 and shotsInClip == 0 or timeLeft >= config['addon-auto_announce_reload']['reload_longer_than'] and config['addon-auto_announce_reload']['reload_longer_than'] > 0:
            if last_timeLeft < timeLeft:
                if last_timeLeft != -1:
                    BigWorld.callback(0.1, lambda : g_sessionProvider.shared.chatCommands.sendReloadingCommand())
                last_timeLeft = timeLeft
    else:
        last_timeLeft = 0


def new_shoot(isRepeat = False, gunIndex = 0):
    global last_enemy_killed_time
    if howitzer:
        cancelLockedShotDistance()
    if isRepeat == False and bw_player._PlayerAvatar__autoAimVehID == 0:
        target = BigWorld.target()
        if target and isinstance(target, Vehicle.Vehicle):
            if not target.isAlive() and target.id == last_enemy_killed_id and time.time() - last_enemy_killed_time < 1.5 and config.get('addon-dead_shot_blocker', False):
                if d:
                    MYLOG('Saving a dead-shot (direct)')
                bw_player.soundNotifications.play('target_unlocked')
                last_enemy_killed_time = 0
                return
            if target.isAlive() and allies_alive.has_key(target.id) and config.get('addon-ally_shot_blocker', False) and not bw_player.arena.vehicles[target.id]['isTeamKiller']:
                if d:
                    MYLOG('Blocking an ally-shot')
                return
        elif time.time() - last_enemy_killed_time < 1.5 and config.get('addon-dead_shot_blocker', False) and findTarget({last_enemy_killed_id: True}) and findTarget(enemies_alive) is None:
            if d:
                MYLOG('Saving a dead-shot (proximity)')
            bw_player.soundNotifications.play('target_unlocked')
            return
    old_shoot(isRepeat)
    return


if config['addon-auto_announce_reload']['enabled'] and config['addon-auto_announce_reload']['only_with_C']:
    clip_reload_with_double_C_delay_cb = 0
    if config['addon-auto_announce_reload']['clip_reload_with_double_C']:

        def sendReloadingCommand():
            global clip_reload_with_double_C_delay_cb
            if d:
                MYLOG('sendReloadingCommand')
            clip_reload_with_double_C_delay_cb = 0
            g_sessionProvider.shared.chatCommands.sendReloadingCommand()


        def new_reloadPartialClip(self, avatar = None):
            global clip_reload_with_double_C_delay_cb
            if clip_reload_with_double_C_delay_cb:
                if d:
                    MYLOG('new_reloadPartialClip with clip_reload_with_double_C_delay_cb')
                BigWorld.cancelCallback(clip_reload_with_double_C_delay_cb)
                clip_reload_with_double_C_delay_cb = 0
                old_reloadPartialClip(self, avatar)
                if not config['addon-auto_announce_reload']['clip_reload']:
                    BigWorld.callback(0.25, lambda : g_sessionProvider.shared.chatCommands.sendReloadingCommand())
            else:
                if d:
                    MYLOG('new_reloadPartialClip (first)')
                clip_reload_with_double_C_delay_cb = BigWorld.callback(config['addon-auto_announce_reload']['second_C_timeout'], sendReloadingCommand)


    else:

        def new_reloadPartialClip(self, avatar = None):
            old_reloadPartialClip(self, avatar)
            BigWorld.callback(0.1, lambda : g_sessionProvider.shared.chatCommands.sendReloadingCommand())


    from gui.battle_control.controllers.consumables.ammo_ctrl import AmmoController
    old_reloadPartialClip = AmmoController.reloadPartialClip
    AmmoController.reloadPartialClip = new_reloadPartialClip

def __onVehicleStateUpdated(state, value):
    if state == VEHICLE_VIEW_STATE.OBSERVED_BY_ENEMY and value and bonusType not in [ARENA_BONUS_TYPE.REGULAR, ARENA_BONUS_TYPE.EVENT_BATTLES, ARENA_BONUS_TYPE.EPIC_BATTLE]:
        if d:
            MYLOG('Asking for help when spotted')
        g_sessionProvider.shared.chatCommands.sendCommand('HELPME')


def __onVehicleFeedbackReceived(eventID, vehicleID, value):
    if eventID == FEEDBACK_EVENT_ID.ENTITY_IN_FOCUS and value and enemies_alive.has_key(vehicleID) and (snap_on_focus or BigWorld.isKeyDown(key_CMD_CM_LOCK_TARGET) and config['time_snapping']['lock_on_pressed']):
        lock.acquire()
        try:
            if bw_player._PlayerAvatar__autoAimVehID == 0:
                cancelTimeSnapping()
                if isinstance(bw_player.inputHandler.ctrl, _TrajectoryControlMode):
                    if d:
                        MYLOG('_TrajectoryControlMode used (VEHICLE_IN_FOCUS)')
                else:
                    if d:
                        MYLOG('target highlighted - locking')
                    new_autoAim(BigWorld.entity(vehicleID))
        finally:
            lock.release()


def finishTimeSnapping():
    global snap_on_focus
    global snap_on_focus_delay_cb
    snap_on_focus = False
    snap_on_focus_delay_cb = 0
    if d:
        MYLOG('finishing time_snapping')
    lock.acquire()
    try:
        if bw_player._PlayerAvatar__autoAimVehID == 0 and indicator:
            indicator.setVisible(False)
    finally:
        lock.release()

    if howitzer:
        cancelLockedShotDistance()


def cancelTimeSnapping():
    if snap_on_focus_delay_cb:
        BigWorld.cancelCallback(snap_on_focus_delay_cb)
    finishTimeSnapping()


from AvatarInputHandler import AimingSystems
locked_shot_distance = 0
if config['addon-howitzer_distance_locker'] > 0:

    def new_getDesiredShotPointUncached(start, dir, onlyOnGround, isStrategicMode, terrainOnlyCheck):
        global locked_shot_distance
        point = old_getDesiredShotPointUncached(start, dir, onlyOnGround, isStrategicMode, terrainOnlyCheck)
        if point and locked_shot_distance:
            if start.flatDistTo(point) > locked_shot_distance:
                point = start + dir.scale(locked_shot_distance)
        return point


    old_getDesiredShotPointUncached = AimingSystems._getDesiredShotPointUncached

    def lockShotDistance():
        if d:
            MYLOG('shot distance locking...')
        if locked_shot_distance:
            cancelLockedShotDistance()
        else:
            target = findTarget(enemies_alive)
            if target:
                recalculateDistance(target, True)
                if d:
                    MYLOG('shot distance locked at %d' % locked_shot_distance)
            elif d:
                MYLOG('no target available')


    def removeEdge(vehicle):
        target = BigWorld.target()
        if target and target.id == vehicle.id:
            return
        vehicle.removeEdge()


    def recalculateDistance(target, force = False):
        global locked_shot_distance
        if locked_shot_distance or force:
            if target.inWorld:
                locked_shot_distance = bw_player.vehicle.position.flatDistTo(target.position)
                BigWorld.callback(0.25, lambda : recalculateDistance(target))


    def cancelLockedShotDistance():
        global locked_shot_distance
        if locked_shot_distance:
            if d:
                MYLOG('cancelling shot distance lock')
            locked_shot_distance = 0


if config.get('addon-ny_box_opener', False) > 0 and False:
    from skeletons.new_year import INewYearController
    newYearController = dependency.instance(INewYearController)
    from items.new_year_types import NY_STATE

    def my_onStateChanged(state):
        if d:
            MYLOG('my_onStateChanged', state)
        if state in NY_STATE.ENABLED:
            ordered = newYearController.boxStorage.getOrderedBoxes()
            for descr, count in ordered:
                if descr.id == 'ny18:box:r':
                    if count > 0:
                        if d:
                            MYLOG('random boxes', count)
                        BigWorld.callback(2, lambda : openRandomBox(count))
                    return


    def openRandomBox(times):
        if times:
            newYearController.boxStorage.open('ny18:box:r')
            BigWorld.callback(2, lambda : openRandomBox(times - 1))


    newYearController.onStateChanged += my_onStateChanged
    from gui.game_control.AwardController import _NYBoxesHandler
    from gui.shared import EVENT_BUS_SCOPE, g_eventBus, events
    from gui.shared.utils.functions import getViewName
    from gui.Scaleform.daapi.settings.views import VIEW_ALIAS
    from collections import defaultdict

    def my_showAward(self, ctx):
        self._NYBoxesHandler__postponedBoxes = defaultdict(int)


    _NYBoxesHandler._showAward = my_showAward
    from gui.Scaleform.daapi.view.lobby.ny.ny_break import NY_Break

    def my__updateShownToysAndSelection(self):
        if d:
            MYLOG('my__updateShownToysAndSelection')
        self._NY_Break__updateSelectedToys()
        toysData = []
        toysTotal = 0
        for toyItemInfo in self._NY_Break__getSortedToys():
            toysTotal += toyItemInfo.count
            if self._NY_Break__checkToy(toyItemInfo.item):
                toyId = toyItemInfo.item.id
                for i in range(0, toyItemInfo.count):
                    isSelected = True
                    toysData.append({'icon': toyItemInfo.item.icon,
                     'id': toyId,
                     'level': toyItemInfo.item.rank,
                     'select': isSelected,
                     'toggle': True,
                     'isCanUpdateNew': False,
                     'canShowContextMenu': False,
                     'isNew': toyItemInfo.newCount > i,
                     'settings': toyItemInfo.item.setting})

        self._NY_Break__selectedToys.clear()
        for index, toyData in enumerate(toysData):
            if toyData['select']:
                if toyData['id'] in self._NY_Break__selectedToys:
                    self._NY_Break__selectedToys[toyData['id']].append(index)
                else:
                    self._NY_Break__selectedToys[toyData['id']] = [index]

        sortedTotal = len(toysData)
        BigWorld.callback(1, lambda : self._NY_Break__updateGain() or self._NY_Break__updateBreakButton())
        return (toysData, toysTotal, sortedTotal)


    NY_Break._NY_Break__updateShownToysAndSelection = my__updateShownToysAndSelection