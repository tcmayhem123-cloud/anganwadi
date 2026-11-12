/**
 * Offline Data Storage & Synchronization Queue via IndexedDB.
 * Meets FR-GM-07, NFR-03, NFR-04: Offline-first data entry for rural field conditions.
 */
class OfflineDatabase {
  constructor() {
    this.dbName = "acgms_offline_store";
    this.dbVersion = 1;
    this.db = null;
  }

  async init() {
    return new Promise((resolve, reject) => {
      const request = indexedDB.open(this.dbName, this.dbVersion);

      request.onupgradeneeded = (event) => {
        const db = event.target.result;
        if (!db.objectStoreNames.contains("measurements_queue")) {
          db.createObjectStore("measurements_queue", { keyPath: "client_id" });
        }
        if (!db.objectStoreNames.contains("vaccines_queue")) {
          db.createObjectStore("vaccines_queue", { keyPath: "client_id" });
        }
      };

      request.onsuccess = (event) => {
        this.db = event.target.result;
        resolve(this.db);
      };

      request.onerror = (event) => {
        console.error("IndexedDB open failed:", event.target.error);
        reject(event.target.error);
      };
    });
  }

  async queueMeasurement(item) {
    if (!this.db) await this.init();
    return new Promise((resolve, reject) => {
      const tx = this.db.transaction("measurements_queue", "readwrite");
      const store = tx.objectStore("measurements_queue");
      const record = {
        ...item,
        client_id: `OFFLINE-MSR-${Date.now()}-${Math.floor(Math.random() * 1000)}`,
        timestamp: new Date().toISOString()
      };
      const req = store.add(record);
      req.onsuccess = () => resolve(record);
      req.onerror = () => reject(req.error);
    });
  }

  async getPendingCount() {
    if (!this.db) await this.init();
    return new Promise((resolve) => {
      const tx = this.db.transaction(["measurements_queue", "vaccines_queue"], "readonly");
      let count = 0;
      
      const msrStore = tx.objectStore("measurements_queue");
      const msrReq = msrStore.count();
      msrReq.onsuccess = () => {
        count += msrReq.result;
        const vacStore = tx.objectStore("vaccines_queue");
        const vacReq = vacStore.count();
        vacReq.onsuccess = () => {
          count += vacReq.result;
          resolve(count);
        };
      };
    });
  }

  async getAllPending() {
    if (!this.db) await this.init();
    return new Promise((resolve) => {
      const tx = this.db.transaction(["measurements_queue", "vaccines_queue"], "readonly");
      const msrStore = tx.objectStore("measurements_queue");
      const vacStore = tx.objectStore("vaccines_queue");

      const msrReq = msrStore.getAll();
      msrReq.onsuccess = () => {
        const vacReq = vacStore.getAll();
        vacReq.onsuccess = () => {
          resolve({
            measurements: msrReq.result || [],
            vaccine_records: vacReq.result || []
          });
        };
      };
    });
  }

  async clearPending() {
    if (!this.db) await this.init();
    return new Promise((resolve) => {
      const tx = this.db.transaction(["measurements_queue", "vaccines_queue"], "readwrite");
      tx.objectStore("measurements_queue").clear();
      tx.objectStore("vaccines_queue").clear();
      tx.oncomplete = () => resolve();
    });
  }
}

window.offlineDB = new OfflineDatabase();
