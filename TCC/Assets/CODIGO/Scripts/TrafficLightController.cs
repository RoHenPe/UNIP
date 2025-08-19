using UnityEngine;
using System.Collections.Generic;

public class CentralCoordinator : MonoBehaviour
{
    public static CentralCoordinator Instance { get; private set; }

    [Header("Configuração de Coordenação")]
    [Range(-1, 1)] public float coordinationBias = 0.0f; // -1 (Favorece EW) a 1 (Favorece NS)

    private List<TrafficLightController> controllers;

    private void Awake()
    {
        if (Instance == null)
        {
            Instance = this;
            controllers = new List<TrafficLightController>();
            DontDestroyOnLoad(gameObject);
        }
        else
        {
            Destroy(gameObject);
        }
    }

    public void RegisterController(TrafficLightController controller)
    {
        if (!controllers.Contains(controller))
        {
            controllers.Add(controller);
        }
    }

    private void Update()
    {
        // Aplica o bias de coordenação a todos os semáforos registrados
        foreach (var controller in controllers)
        {
            controller.ApplyCoordinationBias(coordinationBias);
        }
    }
}