/**
 * E2E 복호화 — Web Crypto API 기반 AES-256-GCM.
 *
 * 로컬 서버에서 암호화된 금융 데이터를 원격 디바이스에서 복호화.
 * 키는 QR 페어링 시 IndexedDB에 저장.
 */

interface EncryptedData {
  iv: string;
  ciphertext: string;
  tag: string;
}

const DB_NAME = "stockvision_keys";
const STORE_NAME = "device_keys";

// ── IndexedDB 키 저장/로드 ──

function openKeyDB(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, 1);
    request.onupgradeneeded = () => {
      const db = request.result;
      if (!db.objectStoreNames.contains(STORE_NAME)) {
        db.createObjectStore(STORE_NAME);
      }
    };
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
}

export async function saveDeviceKey(
  deviceId: string,
  keyBase64: string
): Promise<void> {
  const db = await openKeyDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_NAME, "readwrite");
    tx.objectStore(STORE_NAME).put(keyBase64, deviceId);
    tx.oncomplete = () => resolve();
    tx.onerror = () => reject(tx.error);
  });
}

export async function loadDeviceKey(
  deviceId: string
): Promise<string | null> {
  const db = await openKeyDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_NAME, "readonly");
    const request = tx.objectStore(STORE_NAME).get(deviceId);
    request.onsuccess = () => resolve(request.result ?? null);
    request.onerror = () => reject(request.error);
  });
}

export async function deleteDeviceKey(deviceId: string): Promise<void> {
  const db = await openKeyDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_NAME, "readwrite");
    tx.objectStore(STORE_NAME).delete(deviceId);
    tx.oncomplete = () => resolve();
    tx.onerror = () => reject(tx.error);
  });
}

export async function getStoredDeviceId(): Promise<string | null> {
  const db = await openKeyDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_NAME, "readonly");
    const request = tx.objectStore(STORE_NAME).getAllKeys();
    request.onsuccess = () => {
      const keys = request.result as string[];
      resolve(keys.length > 0 ? keys[0] : null);
    };
    request.onerror = () => reject(request.error);
  });
}

// ── 복호화 ──

function base64ToArrayBuffer(base64: string): ArrayBuffer {
  const binary = atob(base64);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) {
    bytes[i] = binary.charCodeAt(i);
  }
  return bytes.buffer;
}

export async function decrypt(
  encrypted: EncryptedData,
  keyBase64: string
): Promise<object> {
  const keyBytes = base64ToArrayBuffer(keyBase64);
  const iv = base64ToArrayBuffer(encrypted.iv);
  const ciphertext = base64ToArrayBuffer(encrypted.ciphertext);
  const tag = base64ToArrayBuffer(encrypted.tag);

  // AES-GCM은 ciphertext + tag를 연결한 형태로 입력받음
  const ctWithTag = new Uint8Array(ciphertext.byteLength + tag.byteLength);
  ctWithTag.set(new Uint8Array(ciphertext), 0);
  ctWithTag.set(new Uint8Array(tag), ciphertext.byteLength);

  const cryptoKey = await crypto.subtle.importKey(
    "raw",
    keyBytes,
    { name: "AES-GCM" },
    false,
    ["decrypt"]
  );

  const decrypted = await crypto.subtle.decrypt(
    { name: "AES-GCM", iv: new Uint8Array(iv) },
    cryptoKey,
    ctWithTag
  );

  const text = new TextDecoder().decode(decrypted);
  return JSON.parse(text);
}
