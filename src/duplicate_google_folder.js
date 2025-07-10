function copyFoldersForLecturesParallel() {
  const DEST_PARENT_ID = '17oc2PouZuLblMwZixT0KkbAPMblpDzbt';
  const SOURCE_FOLDER_ID = '1q3zYs2jK0HB-AZFUFpV8ZOUayrMAHKiZ';
  const PERMISSIONS_SOURCE_FILE_ID = '1tNAQDq_YoBwozcLxDfcJw7fYK1kIwOEz';
  const DESTINATION_FOLDER_NAME = 'CapeTown';
  const PARALLEL_WORKERS = 13; // Number of parallel workers

  const startTime = new Date().getTime();
  const MAX_EXECUTION_TIME = 5 * 60 * 1000;

  try {
    const emailLists = getEmailsFromFilePermissions(PERMISSIONS_SOURCE_FILE_ID);
    const EMAIL_EDITORS = emailLists.editors;

    const sourceFolder = DriveApp.getFolderById(SOURCE_FOLDER_ID);
    const destParentFolder = DriveApp.getFolderById(DEST_PARENT_ID);

    const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
    const baseFolderName = DESTINATION_FOLDER_NAME || `Copied_${timestamp}`;

    // Create two top-level destination folders
    const instructorTopFolder = destParentFolder.createFolder(`(講師用)${baseFolderName}`);
    const publicTopFolder = destParentFolder.createFolder(baseFolderName);

    Logger.log(`Created instructor folder: ${instructorTopFolder.getName()}`);
    Logger.log(`Created public folder: ${publicTopFolder.getName()}`);

    // First, copy files directly under the parent source folder
    Logger.log(`Copying files directly under parent folder...`);
    copyParentFolderFiles(sourceFolder, instructorTopFolder, publicTopFolder, EMAIL_EDITORS);

    const subfolders = [];
    const subfolderIterator = sourceFolder.getFolders();
    while (subfolderIterator.hasNext()) {
      subfolders.push(subfolderIterator.next());
    }

    Logger.log(`Found ${subfolders.length} subfolders to process with ${PARALLEL_WORKERS} parallel workers`);

    // Process subfolders in parallel batches
    const batchSize = Math.ceil(subfolders.length / PARALLEL_WORKERS);
    const batches = [];
    
    for (let i = 0; i < subfolders.length; i += batchSize) {
      batches.push(subfolders.slice(i, i + batchSize));
    }

    // Process each batch in parallel using Promise.all equivalent
    const results = [];
    for (let batchIndex = 0; batchIndex < batches.length; batchIndex++) {
      const batch = batches[batchIndex];
      
      // Check time limit
      if (new Date().getTime() - startTime > MAX_EXECUTION_TIME) {
        Logger.log(`Execution time limit approached. Processed ${batchIndex} of ${batches.length} batches.`);
        // Save progress for resumption
        saveProgressForResume(instructorTopFolder.getId(), publicTopFolder.getId(), SOURCE_FOLDER_ID, batchIndex * batchSize);
        return;
      }

      Logger.log(`Processing batch ${batchIndex + 1}/${batches.length} with ${batch.length} folders`);
      
      // Process this batch
      const batchResult = processBatchParallel(
        batch,
        instructorTopFolder,
        publicTopFolder,
        EMAIL_EDITORS,
        startTime,
        MAX_EXECUTION_TIME,
        batchIndex * batchSize
      );
      
      results.push(batchResult);
    }

    Logger.log(`All folders copied successfully using parallel processing.`);
  } catch (error) {
    Logger.log(`Error: ${error.toString()}`);
  }
}

function copyParentFolderFiles(sourceFolder, instructorTopFolder, publicTopFolder, editors) {
  Logger.log(`Processing files directly under parent folder: ${sourceFolder.getName()}`);
  
  const files = [];
  const fileIterator = sourceFolder.getFiles();
  while (fileIterator.hasNext()) {
    files.push(fileIterator.next());
  }
  
  if (files.length === 0) {
    Logger.log(`No files found directly under parent folder`);
    return;
  }
  
  Logger.log(`Found ${files.length} files directly under parent folder`);
  
  // Copy files to instructor folder (all files)
  Logger.log(`Copying ${files.length} files to instructor folder...`);
  for (const file of files) {
    try {
      const copy = file.makeCopy(file.getName(), instructorTopFolder);
      setPermissionsOptimizedBatch(copy, editors);
      Logger.log(`  Copied to instructor: ${file.getName()}`);
    } catch (e) {
      Logger.log(`  Failed to copy ${file.getName()} to instructor folder: ${e}`);
    }
  }
  
  // Copy files to public folder (excluding instructor files)
  const publicFiles = files.filter(file => !file.getName().includes('講師'));
  Logger.log(`Copying ${publicFiles.length} files to public folder (excluding instructor files)...`);
  for (const file of publicFiles) {
    try {
      const copy = file.makeCopy(file.getName(), publicTopFolder);
      setPermissionsOptimizedBatch(copy, editors);
      Logger.log(`  Copied to public: ${file.getName()}`);
    } catch (e) {
      Logger.log(`  Failed to copy ${file.getName()} to public folder: ${e}`);
    }
  }
  
  const skippedCount = files.length - publicFiles.length;
  if (skippedCount > 0) {
    Logger.log(`Skipped ${skippedCount} instructor files from public folder`);
  }
}

function processBatchParallel(subfolders, instructorTopFolder, publicTopFolder, editors, startTime, maxTime, startIndex) {
  const workers = [];
  
  // Create worker functions for each subfolder in the batch
  for (let i = 0; i < subfolders.length; i++) {
    const subfolder = subfolders[i];
    const folderIndex = startIndex + i;
    
    workers.push(() => {
      const baseName = subfolder.getName();
      Logger.log(`Worker processing folder ${folderIndex + 1}: ${baseName}`);
      
      try {
        // Create both versions of the folder
        const instructorFolder = instructorTopFolder.createFolder(baseName);
        const publicFolder = publicTopFolder.createFolder(baseName);
        
        // Process instructor version
        const instructorSuccess = copyContentsAndSetPermissionsOptimized(
          subfolder,
          instructorFolder,
          editors,
          startTime,
          maxTime,
          false
        );
        
        // Process public version
        const publicSuccess = copyContentsAndSetPermissionsOptimized(
          subfolder,
          publicFolder,
          editors,
          startTime,
          maxTime,
          true
        );
        
        return {
          success: instructorSuccess && publicSuccess,
          folderName: baseName,
          index: folderIndex
        };
      } catch (error) {
        Logger.log(`Worker error processing ${baseName}: ${error.toString()}`);
        return {
          success: false,
          folderName: baseName,
          index: folderIndex,
          error: error.toString()
        };
      }
    });
  }
  
  // Execute all workers (simulating parallel execution)
  const results = [];
  for (const worker of workers) {
    // Check time limit before each worker
    if (new Date().getTime() - startTime > maxTime) {
      Logger.log(`Time limit reached during batch processing`);
      break;
    }
    
    results.push(worker());
    
    // Small delay to prevent API rate limiting
    Utilities.sleep(100);
  }
  
  return results;
}

function copyContentsAndSetPermissionsOptimized(source, target, editors, startTime, maxTime, skipInstructorContent = false) {
  // Check execution time
  if (new Date().getTime() - startTime > maxTime) {
    Logger.log(`Time limit reached during processing of: ${source.getName()}`);
    return false;
  }
  
  // Set permissions for the folder (editors only) - optimized batch operation
  setPermissionsOptimizedBatch(target, editors);
  
  // Get all files and folders first (batch operation)
  const files = [];
  const subfolders = [];
  
  const fileIterator = source.getFiles();
  while (fileIterator.hasNext()) {
    const file = fileIterator.next();
    
    // Skip files with "講師" in the name if this is for public folders
    if (skipInstructorContent && file.getName().includes('講師')) {
      continue;
    }
    
    files.push(file);
  }
  
  const subfolderIterator = source.getFolders();
  while (subfolderIterator.hasNext()) {
    const subfolder = subfolderIterator.next();
    
    // Skip subfolders with "講師" in the name if this is for public folders
    if (skipInstructorContent && subfolder.getName().includes('講師')) {
      continue;
    }
    
    subfolders.push(subfolder);
  }
  
  Logger.log(`  Processing ${files.length} files and ${subfolders.length} subfolders...`);
  
  // Copy files in optimized batches
  const fileBatchSize = 5; // Smaller batches for better performance
  for (let i = 0; i < files.length; i += fileBatchSize) {
    const batch = files.slice(i, i + fileBatchSize);
    
    // Process file batch with error handling
    const copiedFiles = [];
    for (const file of batch) {
      try {
        const copy = file.makeCopy(file.getName(), target);
        copiedFiles.push(copy);
      } catch (e) {
        Logger.log(`  Failed to copy file ${file.getName()}: ${e}`);
      }
    }
    
    // Set permissions for all copied files in this batch
    setPermissionsForBatch(copiedFiles, editors);
    
    // Minimal delay between batches
    Utilities.sleep(50);
    
    // Check time again
    if (new Date().getTime() - startTime > maxTime) {
      Logger.log(`Time limit reached during file copying`);
      return false;
    }
  }
  
  // Process subfolders with parallel-like approach
  for (const subfolder of subfolders) {
    const newSub = target.createFolder(subfolder.getName());
    const success = copyContentsAndSetPermissionsOptimized(subfolder, newSub, editors, startTime, maxTime, skipInstructorContent);
    if (!success) {
      return false;
    }
  }
  
  return true;
}

function setPermissionsOptimizedBatch(item, editors) {
  const fileId = item.getId();

  try {
    // Remove existing public permissions (batch operation)
    const existingPermissions = Drive.Permissions.list(fileId);
    const publicPermissions = existingPermissions.items.filter(perm => 
      perm.type === 'anyone' || perm.type === 'domain'
    );
    
    // Remove public permissions in batch
    for (const perm of publicPermissions) {
      try {
        Drive.Permissions.remove(fileId, perm.id);
      } catch (e) {
        Logger.log(`Failed to remove public permission: ${e}`);
      }
    }

    // Add editors in batch without notifications
    const permissionInserts = editors.map(email => ({
      'role': 'writer',
      'type': 'user',
      'value': email
    }));
    
    for (const permissionData of permissionInserts) {
      try {
        Drive.Permissions.insert(
          permissionData,
          fileId,
          { 'sendNotificationEmails': false }
        );
      } catch (e) {
        Logger.log(`Failed to add editor (${permissionData.value}): ${e}`);
      }
    }
  } catch (e) {
    Logger.log(`Error setting permissions for ${item.getName()}: ${e}`);
  }

  // Reduced sleep time for better performance
  Utilities.sleep(25);
}

function setPermissionsForBatch(items, editors) {
  for (const item of items) {
    setPermissionsOptimizedBatch(item, editors);
  }
}

function saveProgressForResume(instructorFolderId, publicFolderId, sourceFolderId, processedCount) {
  // Save progress to properties for resumption
  const properties = PropertiesService.getScriptProperties();
  properties.setProperties({
    'resume_instructor_folder': instructorFolderId,
    'resume_public_folder': publicFolderId,
    'resume_source_folder': sourceFolderId,
    'resume_processed_count': processedCount.toString(),
    'resume_timestamp': new Date().getTime().toString()
  });
  
  Logger.log(`Progress saved: ${processedCount} folders processed`);
  Logger.log(`To resume, call: resumeCopyFromFolderParallel()`);
}

function resumeCopyFromFolderParallel() {
  const PERMISSIONS_SOURCE_FILE_ID = '1tNAQDq_YoBwozcLxDfcJw7fYK1kIwOEz';
  const PARALLEL_WORKERS = 3;
  
  const properties = PropertiesService.getScriptProperties();
  const instructorFolderId = properties.getProperty('resume_instructor_folder');
  const publicFolderId = properties.getProperty('resume_public_folder');
  const sourceFolderId = properties.getProperty('resume_source_folder');
  const processedCount = parseInt(properties.getProperty('resume_processed_count') || '0');
  
  if (!instructorFolderId || !publicFolderId || !sourceFolderId) {
    Logger.log('No resume data found. Please run the main function first.');
    return;
  }
  
  Logger.log(`Resuming from folder ${processedCount + 1}`);
  
  const startTime = new Date().getTime();
  const MAX_EXECUTION_TIME = 5 * 60 * 1000;
  
  try {
    const emailLists = getEmailsFromFilePermissions(PERMISSIONS_SOURCE_FILE_ID);
    const EMAIL_EDITORS = emailLists.editors;
    
    const sourceFolder = DriveApp.getFolderById(sourceFolderId);
    const instructorDestFolder = DriveApp.getFolderById(instructorFolderId);
    const publicDestFolder = DriveApp.getFolderById(publicFolderId);
    
    const subfolders = [];
    const subfolderIterator = sourceFolder.getFolders();
    while (subfolderIterator.hasNext()) {
      subfolders.push(subfolderIterator.next());
    }
    
    const remainingFolders = subfolders.slice(processedCount);
    Logger.log(`Resuming with ${remainingFolders.length} remaining folders`);
    
    // Also copy parent folder files if this is the first resume (processedCount = 0)
    if (processedCount === 0) {
      Logger.log(`Copying parent folder files during resume...`);
      copyParentFolderFiles(sourceFolder, instructorDestFolder, publicDestFolder, EMAIL_EDITORS);
    }
    
    // Process remaining folders in parallel batches
    const batchSize = Math.ceil(remainingFolders.length / PARALLEL_WORKERS);
    const batches = [];
    
    for (let i = 0; i < remainingFolders.length; i += batchSize) {
      batches.push(remainingFolders.slice(i, i + batchSize));
    }
    
    for (let batchIndex = 0; batchIndex < batches.length; batchIndex++) {
      const batch = batches[batchIndex];
      
      if (new Date().getTime() - startTime > MAX_EXECUTION_TIME) {
        Logger.log(`Execution time limit approached during resume.`);
        saveProgressForResume(instructorFolderId, publicFolderId, sourceFolderId, processedCount + (batchIndex * batchSize));
        return;
      }
      
      Logger.log(`Processing resume batch ${batchIndex + 1}/${batches.length}`);
      
      processBatchParallel(
        batch,
        instructorDestFolder,
        publicDestFolder,
        EMAIL_EDITORS,
        startTime,
        MAX_EXECUTION_TIME,
        processedCount + (batchIndex * batchSize)
      );
    }
    
    // Clear resume data on successful completion
    properties.deleteProperty('resume_instructor_folder');
    properties.deleteProperty('resume_public_folder');
    properties.deleteProperty('resume_source_folder');
    properties.deleteProperty('resume_processed_count');
    properties.deleteProperty('resume_timestamp');
    
    Logger.log(`Resume operation completed successfully.`);
  } catch (error) {
    Logger.log(`Resume error: ${error.toString()}`);
  }
}

// Keep the original helper functions
function getEmailsFromFilePermissions(fileId) {
  const editors = [];
  
  try {
    const permissions = Drive.Permissions.list(fileId);
    Logger.log(`Found ${permissions.items.length} permissions on source file`);
    
    for (const permission of permissions.items) {
      if (permission.type !== 'user') {
        continue;
      }
      
      if (!permission.emailAddress) {
        continue;
      }
      
      const email = permission.emailAddress;
      
      if (permission.role === 'writer' || permission.role === 'owner') {
        if (!editors.includes(email)) {
          editors.push(email);
          Logger.log(`Added editor: ${email}`);
        }
      }
    }
    
    if (editors.length === 0) {
      Logger.log('No editors found, adding current user as default editor');
      const currentUser = Session.getActiveUser().getEmail();
      editors.push(currentUser);
    }
    
    Logger.log(`Final editors list: ${editors.join(', ')}`);
    
    return {
      editors: editors
    };
    
  } catch (error) {
    Logger.log(`Error getting permissions from file: ${error.toString()}`);
    
    return {
      editors: [Session.getActiveUser().getEmail()]
    };
  }
}
