#import <Cocoa/Cocoa.h>
#include <unistd.h>
#include <stdlib.h>
#include <string.h>

@interface OpenT1DDelegate : NSObject <NSApplicationDelegate>
@property(strong) NSTask *worker;
@property(strong) NSFileHandle *log;
@property(copy) NSString *logPath;
@property BOOL stopping;
@end

@implementation OpenT1DDelegate
- (void)showFailure:(NSString *)message {
    [NSApp activateIgnoringOtherApps:YES];
    NSAlert *alert = [[NSAlert alloc] init];
    alert.messageText = @"OpenT1D could not start or stop";
    alert.informativeText = [message stringByAppendingFormat:@"\n\nStartup log: %@", self.logPath ?: @"unavailable"];
    [alert addButtonWithTitle:@"OK"];
    [alert runModal];
}
- (void)launch:(BOOL)primary {
    NSURL *payload = [[[NSBundle mainBundle] resourceURL] URLByAppendingPathComponent:@"payload"];
    NSURL *python = [payload URLByAppendingPathComponent:@"runtime/bin/python3.12"];
    NSURL *source = [payload URLByAppendingPathComponent:@"app"];
    NSTask *task = [[NSTask alloc] init];
    task.executableURL = python;
    task.currentDirectoryURL = source;
    NSMutableArray *arguments = [NSMutableArray arrayWithArray:@[@"-I", @"-B", @"-S", [[source URLByAppendingPathComponent:@"packaging/mac/bootstrap.py"] path]]];
    for (NSString *argument in [[[NSProcessInfo processInfo] arguments] subarrayWithRange:NSMakeRange(1, [[[NSProcessInfo processInfo] arguments] count] - 1)]) {
        if (![argument hasPrefix:@"-psn_"]) [arguments addObject:argument];
    }
    task.arguments = arguments;
    NSMutableDictionary *environment = [[[NSProcessInfo processInfo] environment] mutableCopy];
    for (NSString *key in [environment allKeys]) {
        if ([key hasPrefix:@"PYTHON"] || [key hasPrefix:@"UV_"] || [key hasPrefix:@"DYLD_"] || [key isEqualToString:@"VIRTUAL_ENV"] || [key isEqualToString:@"__PYVENV_LAUNCHER__"]) [environment removeObjectForKey:key];
    }
    environment[@"PATH"] = @"/usr/bin:/bin:/usr/sbin:/sbin";
    task.environment = environment;
    task.standardOutput = self.log;
    task.standardError = self.log;
    task.terminationHandler = ^(NSTask *finished) {
        dispatch_async(dispatch_get_main_queue(), ^{
            if (finished.terminationStatus != 0) {
                [self showFailure:@"The included interpreter reported a startup or shutdown error. Your saved analyses remain outside the application."];
            }
            if (primary) {
                if (self.stopping) [NSApp replyToApplicationShouldTerminate:YES];
                else [NSApp terminate:nil];
            }
        });
    };
    NSError *error = nil;
    if (![task launchAndReturnError:&error]) {
        [self showFailure:[error localizedDescription]];
        if (primary) [NSApp terminate:nil];
    } else if (primary) self.worker = task;
}
- (void)applicationDidFinishLaunching:(NSNotification *)notification {
    NSString *template = [NSTemporaryDirectory() stringByAppendingPathComponent:@"OpenT1D-startup-XXXXXX.log"];
    char *name = strdup([template fileSystemRepresentation]);
    int descriptor = mkstemps(name, 4);
    if (descriptor < 0) {
        free(name);
        [self showFailure:@"A private startup log could not be created."];
        [NSApp terminate:nil];
        return;
    }
    self.logPath = [[NSFileManager defaultManager] stringWithFileSystemRepresentation:name length:strlen(name)];
    free(name);
    self.log = [[NSFileHandle alloc] initWithFileDescriptor:descriptor closeOnDealloc:YES];
    NSMenu *menu = [[NSMenu alloc] init];
    NSMenuItem *application = [[NSMenuItem alloc] init];
    NSMenu *items = [[NSMenu alloc] init];
    [items addItemWithTitle:@"Quit OpenT1D" action:@selector(terminate:) keyEquivalent:@"q"];
    application.submenu = items;
    [menu addItem:application];
    [NSApp setMainMenu:menu];
    [self launch:YES];
}
- (BOOL)applicationShouldHandleReopen:(NSApplication *)sender hasVisibleWindows:(BOOL)visible {
    if (self.worker.running) [self launch:NO];
    return YES;
}
- (NSApplicationTerminateReply)applicationShouldTerminate:(NSApplication *)sender {
    if (self.worker.running) {
        self.stopping = YES;
        [self.worker terminate];
        return NSTerminateLater;
    }
    return NSTerminateNow;
}
@end

int main(int argc, const char *argv[]) {
    @autoreleasepool {
        NSApplication *app = [NSApplication sharedApplication];
        OpenT1DDelegate *delegate = [[OpenT1DDelegate alloc] init];
        app.delegate = delegate;
        [app run];
    }
    return 0;
}
