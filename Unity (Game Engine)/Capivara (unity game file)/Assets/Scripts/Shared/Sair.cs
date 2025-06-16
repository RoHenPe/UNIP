using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.SceneManagement;

public class SairCena : MonoBehaviour
{
    public void Home(string Inicio)
    {
        SceneManager.LoadScene(Inicio);
    }
}
