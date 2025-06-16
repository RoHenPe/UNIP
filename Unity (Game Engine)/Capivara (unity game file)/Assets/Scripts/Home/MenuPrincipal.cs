using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.SceneManagement;

public class MenuPrincipal : MonoBehaviour
{
    [SerializeField] private string Cutscene;

    [SerializeField] private string Logon;

    [SerializeField] private string information;

    public void CutsceneCena()
    {
        SceneManager.LoadScene(Cutscene);
    }
    public void LogonCena()
    {
        SceneManager.LoadScene(Logon);
    }
        public void informationCena()
    {
        SceneManager.LoadScene(information);
    }
    
}
