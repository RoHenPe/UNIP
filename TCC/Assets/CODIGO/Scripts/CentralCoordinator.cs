using UnityEngine;
using System.Collections.Generic;

public class CentralCoordinator : MonoBehaviour
{
    // Acessível de qualquer lugar
    public static CentralCoordinator Instance;

    private List<TrafficLightController> registeredControllers = new List<TrafficLightController>();

    [Header("Configurações Globais")]
    public float coordinationInterval = 5.0f; // Intervalo para reavaliar a coordenação

    private void Awake()
    {
        // Implementa o padrão Singleton para garantir uma única instância
        if (Instance == null)
        {
            Instance = this;
            DontDestroyOnLoad(gameObject);
        }
        else
        {
            Destroy(gameObject);
        }
    }

    private void Start()
    {
        InvokeRepeating(nameof(UpdateCoordination), coordinationInterval, coordinationInterval);
    }

    public void RegisterController(TrafficLightController controller)
    {
        if (!registeredControllers.Contains(controller))
        {
            registeredControllers.Add(controller);
        }
    }

    private void UpdateCoordination()
    {
        // Lógica de coordenação
        // Este é um exemplo simples que equilibra o tráfego total
        int totalDemandNS = 0;
        int totalDemandEW = 0;

        foreach (var controller in registeredControllers)
        {
            totalDemandNS += controller.DemandNS;
            totalDemandEW += controller.DemandEW;
        }

        // Se uma via tem muito mais carros, a coordenação favorece ela.
        if (totalDemandNS > totalDemandEW)
        {
            foreach (var controller in registeredControllers)
            {
                controller.ApplyCoordinationBias(1.0f); // Favorece o tráfego Norte-Sul
            }
        }
        else if (totalDemandEW > totalDemandNS)
        {
            foreach (var controller in registeredControllers)
            {
                controller.ApplyCoordinationBias(-1.0f); // Favorece o tráfego Leste-Oeste
            }
        }
        else
        {
            // Se a demanda é igual, não há viés
            foreach (var controller in registeredControllers)
            {
                controller.ApplyCoordinationBias(0);
            }
        }
    }
}