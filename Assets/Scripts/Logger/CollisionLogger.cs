using UnityEngine;
using Simulator.Logging;

namespace Simulator.LoggingModules
{
    public class CollisionLogger : MonoBehaviour, ILoggingProvider
    {
        private bool collisionThisFrame = false;
        private int collisionCount = 0;

        private float startTime;
        public float ignoreInitialTime = 0.5f; // ignore initial collisions

        void Start()
        {
            startTime = Time.time;
        }

        public string GetHeader()
        {
            // collision_flag: 1 if a collision occurred this frame, 0 otherwise
            // collision_count: total number of collisions recorded
            return "collision_flag,collision_count";
        }

        public string GetLogLine()
        {
            int flag = collisionThisFrame ? 1 : 0;
            collisionThisFrame = false; // reset state to avoid continuous logging
            return $"{flag},{collisionCount}";
        }

        void OnCollisionEnter(Collision collision)
        {
            if (Time.time - startTime < ignoreInitialTime)
            {
                Debug.Log($"[CollisionLogger] Ignored startup collision with: {collision.gameObject.name}");
                return;
            }

            collisionThisFrame = true;
            collisionCount++;
        }

        public int GetCollisionCount()
        {
            return collisionCount;
        }
    }
}
