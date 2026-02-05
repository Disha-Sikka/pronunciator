import 'dart:convert';
import 'dart:io';
import 'dart:async'; // ✅ REQUIRED for Timer

import 'package:flutter/material.dart';
import 'package:flutter_sound/flutter_sound.dart';
import 'package:path_provider/path_provider.dart';
import 'package:permission_handler/permission_handler.dart';
import 'package:http/http.dart' as http;

void main() {
  runApp(const MyApp());
}

class MyApp extends StatelessWidget {
  const MyApp({super.key});

  @override
  Widget build(BuildContext context) {
    return const MaterialApp(
      debugShowCheckedModeBanner: false,
      home: RecorderPage(),
    );
  }
}

class RecorderPage extends StatefulWidget {
  const RecorderPage({super.key});

  @override
  State<RecorderPage> createState() => _RecorderPageState();
}

class _RecorderPageState extends State<RecorderPage> {
  final FlutterSoundRecorder _recorder = FlutterSoundRecorder();

  bool isRecording = false;
  bool isSending = false;
  String? filePath;

  int secondsRecorded = 0;
  Timer? timer;

  @override
  void initState() {
    super.initState();
    initRecorder();
  }

  Future<void> initRecorder() async {
    await Permission.microphone.request();
    await _recorder.openRecorder();
  }

  Future<void> startRecording() async {
    final dir = await getApplicationDocumentsDirectory();
    filePath = '${dir.path}/word.wav';

    await _recorder.startRecorder(
      toFile: filePath,
      codec: Codec.pcm16WAV,
      sampleRate: 16000,
    );

    secondsRecorded = 0;
    timer = Timer.periodic(const Duration(seconds: 1), (_) {
      if (mounted) {
        setState(() => secondsRecorded++);
      }
    });

    setState(() => isRecording = true);
  }

  Future<void> stopRecording() async {
    await _recorder.stopRecorder();
    timer?.cancel();

    setState(() => isRecording = false);
  }

  Future<void> sendAudioToBackend() async {
    if (filePath == null) return;

    
    setState(() => isSending = true);

    try {
      final uri = Uri.parse(
        "http://192.168.1.22:8000/check-pronunciation", // ⚠️ YOUR LAPTOP IP
      );

      final request = http.MultipartRequest("POST", uri)
        ..fields["word"] = "thought"
        ..files.add(
          await http.MultipartFile.fromPath("audio", filePath!),
        );

      final streamedResponse = await request
          .send()
          .timeout(const Duration(seconds: 10));

      final responseBody =
          await streamedResponse.stream.bytesToString();

      final data = jsonDecode(responseBody);

      if (!mounted) return;

      showDialog(
        context: context,
        builder: (_) => AlertDialog(
          title: const Text("Pronunciation Result"),
          content: Text(
            "Word: ${data['word']}\nScore: ${data['score']}",
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(context),
              child: const Text("OK"),
            )
          ],
        ),
      );
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text("ERROR: $e")),
      );
    } finally {
      setState(() => isSending = false);
    }
  }

  @override
  void dispose() {
    timer?.cancel();
    _recorder.closeRecorder();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text("Pronunciation Recorder"),
      ),
      body: Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              ElevatedButton(
                onPressed: isRecording ? stopRecording : startRecording,
                child: Text(
                  isRecording ? "Stop Recording" : "Start Recording",
                ),
              ),

              const SizedBox(height: 12),

              if (isRecording)
                Text(
                  "Recording... $secondsRecorded s",
                  style: const TextStyle(
                    color: Colors.red,
                    fontWeight: FontWeight.bold,
                  ),
                ),

              const SizedBox(height: 16),

              if (filePath != null)
                Text(
                  "Saved file:\n$filePath",
                  textAlign: TextAlign.center,
                ),

              const SizedBox(height: 24),

              ElevatedButton(
                onPressed:
                    (filePath == null || isSending) ? null : sendAudioToBackend,
                child: isSending
                    ? const CircularProgressIndicator()
                    : const Text("Check Pronunciation"),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
