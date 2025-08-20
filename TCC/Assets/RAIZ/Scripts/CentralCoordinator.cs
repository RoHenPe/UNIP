using UnityEngine;
using System.Collections.Generic;
using System.IO;
using System;
using System.Text;
using System.Threading.Tasks;

public class CentralCoordinator : MonoBehaviour
{
    public List<TrafficLightController> trafficLights;
    public List<YoloCameraSimulator> yoloCameras; // Referência às câmeras
    public float updateFrequency = 1f;
    private float lastUpdateTime = 0f;
    public bool isDynamicMode = true; // Define o modo de simulação
    private string logFilePath;

    void Start()
    {
        trafficLights = new List<TrafficLightController>(FindObjectsOfType<TrafficLightController>());
        yoloCameras = new List<YoloCameraSimulator>(FindObjectsOfType<YoloCameraSimulator>());

        // Defina o caminho do arquivo de log, simulando a pasta para MariaDB
        string dbOutputPath = Path.Combine(Application.dataPath, "..", "malha_unity", "dados_mariadb");
        Directory.CreateDirectory(dbOutputPath);
        logFilePath = Path.Combine(dbOutputPath, "unity_data.csv");
        
        // Crie o cabeçalho do arquivo CSV
        string header = "timestamp,total_vehicles,emergency_vehicles,buses,cars,intersection_data\n";
        File.WriteAllText(logFilePath, header);
    }

    void Update()
    {
        if (Time.time - lastUpdateTime >= updateFrequency)
        {
            if (isDynamicMode)
            {
                CoordinateTrafficLightsDynamic();
            }
            else
            {
                CoordinateTrafficLightsConservative();
            }
            LogSimulationData();
            lastUpdateTime = Time.time;
        }
    }

    void CoordinateTrafficLightsDynamic()
    {
        if (trafficLights == null || trafficLights.Count == 0 || yoloCameras.Count == 0) return;

        foreach (var tl in trafficLights)
        {
            // Lógica para obter a demanda de tráfego de forma mais realista (exemplo)
            // Associe câmeras a semáforos específicos
            YoloCameraSimulator cameraNS = yoloCameras.Find(c => c.name.Contains("Camera_NS"));
            YoloCameraSimulator cameraEW = yoloCameras.Find(c => c.name.Contains("Camera_EW"));

            float demandNS = (cameraNS != null) ? cameraNS.DetectedVehicleCount : 0;
            float demandEW = (cameraEW != null) ? cameraEW.DetectedVehicleCount : 0;
            
            tl.UpdateDemand(demandNS, demandEW);

            // Priorização de veículos de emergência
            if (cameraNS != null && cameraNS.GetVehicleCount("emergency") > 0)
            {
                tl.SetState(TrafficLightController.LightState.Green);
            }
            else if (cameraEW != null && cameraEW.GetVehicleCount("emergency") > 0)
            {
                tl.SetState(TrafficLightController.LightState.Red);
            }
            else
            {
                if (tl.DemandNS > tl.DemandEW)
                {
                    tl.SetState(TrafficLightController.LightState.Green);
                }
                else if (tl.DemandEW > tl.DemandNS)
                {
                    tl.SetState(TrafficLightController.LightState.Red);
                }
                else
                {
                    // Mantém o estado atual se as demandas forem iguais
                }
            }
        }
    }

    void CoordinateTrafficLightsConservative()
    {
        if (trafficLights == null || trafficLights.Count == 0) return;

        // Lógica de tempo fixo. Exemplo: 30s Verde NS, 3s Amarelo, 30s Verde EW
        float fixedGreenDuration = 30f;
        float fixedYellowDuration = 3f;
        float totalPhaseDuration = fixedGreenDuration + fixedYellowDuration;

        foreach (var tl in trafficLights)
        {
            float timeInPhase = Time.time % (2 * totalPhaseDuration);
            
            if (timeInPhase < fixedGreenDuration)
            {
                tl.SetState(TrafficLightController.LightState.Green);
            }
            else if (timeInPhase < fixedGreenDuration + fixedYellowDuration)
            {
                tl.SetState(TrafficLightController.LightState.Yellow);
            }
            else if (timeInPhase < fixedGreenDuration + fixedYellowDuration + fixedGreenDuration)
            {
                tl.SetState(TrafficLightController.LightState.Red);
            }
            else
            {
                tl.SetState(TrafficLightController.LightState.Yellow);
            }
        }
    }

    void LogSimulationData()
    {
        int totalVehicles = 0;
        int emergencyVehicles = 0;
        int buses = 0;
        int cars = 0;
        StringBuilder intersectionData = new StringBuilder();

        foreach (var cam in yoloCameras)
        {
            emergencyVehicles += cam.GetVehicleCount("emergency");
            buses += cam.GetVehicleCount("bus");
            cars += cam.GetVehicleCount("car");
            totalVehicles += cam.DetectedVehicleCount;
            intersectionData.Append($"Intersection_{cam.name}:EW_Queue={cam.GetVehicleCount("car")},NS_Queue={cam.GetVehicleCount("car")};");
        }
        
        string line = $"{DateTime.Now.ToString("o")},{totalVehicles},{emergencyVehicles},{buses},{cars},{intersectionData.ToString()}\n";
        File.AppendAllText(logFilePath, line);

        // Aviso para o usuário sobre a integração com o banco de dados
        if (Time.frameCount % 100 == 0) // Para não poluir o console
        {
            Debug.Log($"Dados de simulação salvos em {logFilePath}. Este arquivo deve ser enviado para o EC2 e depois para o MariaDB.");
        }
    }
}