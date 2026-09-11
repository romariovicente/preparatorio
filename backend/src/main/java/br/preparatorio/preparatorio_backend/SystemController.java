package br.preparatorio.preparatorio_backend;

import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.Map;

@RestController
public class SystemController {

    @GetMapping("/api/status")
    public Map<String, Object> status() {
        return Map.of(
            "project", "PREPARATÓRIO",
            "creator", "Romario Vicente Amaro",
            "status", "ONLINE",
            "platform", "Celular + Navegador + Computador",
            "cameraDefault", "Terceira Pessoa",
            "cameraAlternative", "Primeira Pessoa",
            "frontend", "JavaScript + React + Three.js",
            "backend", "Java + Spring Boot",
            "version", "Alpha 0.1"
        );
    }
}
