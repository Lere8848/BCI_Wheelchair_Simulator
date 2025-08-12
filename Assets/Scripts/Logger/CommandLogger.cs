using UnityEngine;
using Simulator.Logging;
using System;

namespace Simulator.LoggingModules
{
    public class CommandLogger : MonoBehaviour, ILoggingProvider
    {
        private float lastCmdTime = -1f;
        private Vector3 lastLinearVel = Vector3.zero;
        private Vector3 lastAngularVel = Vector3.zero;

        public string GetHeader()
        {
            return "cmd_time,cmd_linear_x,cmd_linear_z,cmd_angular_y";
        }

        public string GetLogLine()
        {
            return $"{lastCmdTime:F3},{lastLinearVel.x:F3},{lastLinearVel.z:F3},{lastAngularVel.y:F3}";
        }

        // External call: controller calls this method whenever it receives cmd_vel
        public void RecordVelocityCommand(Vector3 linear, Vector3 angular)
        {
            lastCmdTime = Time.time;
            lastLinearVel = linear;
            lastAngularVel = angular;
        }
    }
}
