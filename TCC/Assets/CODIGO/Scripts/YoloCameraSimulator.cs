using UnityEngine;
using System.Collections.Generic;

public class YoloCameraSimulator : MonoBehaviour
{
    private HashSet<VehicleAI> detectedVehicles = new HashSet<VehicleAI>();

    public int DetectedVehicleCount => detectedVehicles.Count;

    // A caixa de detecção deve ser um trigger
    private void OnTriggerEnter(Collider other)
    {
        if (other.CompareTag("Vehicle"))
        {
            VehicleAI vehicle = other.GetComponent<VehicleAI>();
            if (vehicle != null)
            {
                detectedVehicles.Add(vehicle);
            }
        }
    }

    private void OnTriggerExit(Collider other)
    {
        if (other.CompareTag("Vehicle"))
        {
            VehicleAI vehicle = other.GetComponent<VehicleAI>();
            if (vehicle != null)
            {
                detectedVehicles.Remove(vehicle);
            }
        }
    }
}