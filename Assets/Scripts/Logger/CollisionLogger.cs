using UnityEngine;
using Simulator.Logging;

namespace Simulator.LoggingModules
{
    public class CollisionLogger : MonoBehaviour, ILoggingProvider
    {
        private bool collisionThisFrame = false;
        private int collisionCount = 0;

        public string GetHeader()
        {
            // collision_flag: 1 if a collision occurred this frame, 0 otherwise
            // collision_count: total number of collisions recorded
            return "collision_flag,collision_count";
        }

        public string GetLogLine()
        {
            int flag = collisionThisFrame ? 1 : 0;
            collisionThisFrame = false; // 重置状态，避免持续记录
            return $"{flag},{collisionCount}";
        }

        void OnCollisionEnter(Collision collision) // 当发生碰撞时调用
        {
            // 记录碰撞标志和次数（可加 tag 限定）
            collisionThisFrame = true;
            collisionCount++;
        }
    }
}
