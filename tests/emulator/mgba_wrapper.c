/* Tiny C wrapper around libmgba so Python ctypes can drive the emulator without
 * reverse-engineering the C struct member offsets. Compile with:
 *   gcc -shared -fPIC -O2 mgba_wrapper.c -lmgba -o mgba_wrapper.so
 */
#include <stdbool.h>
#include <stdint.h>
#include <stddef.h>

struct mCore;

/* Forward declarations of libmgba symbols we use. */
extern struct mCore* mCoreFind(const char* path);
extern bool mCoreLoadFile(struct mCore* core, const char* path);
extern bool mCoreAutoloadSave(struct mCore* core);
extern bool mCoreLoadSaveFile(struct mCore* core, const char* path, bool temporary);
extern void* mCoreGetMemoryBlock(struct mCore* core, uint32_t start, size_t* size);

/* The struct mCore has function-pointer members. To avoid hard-coding their
 * offsets we expose tiny inline wrappers that call them through the layout
 * known to the compiler at build time. */
struct _mCoreOpaque;
typedef struct _mCoreOpaque mCoreOpaque;

/* This header pulls in the real layout. */
#include <mgba/core/core.h>

bool wrapper_init(struct mCore* core) {
    return core->init(core);
}

void wrapper_deinit(struct mCore* core) {
    core->deinit(core);
}

void wrapper_reset(struct mCore* core) {
    core->reset(core);
}

void wrapper_run_frame(struct mCore* core) {
    core->runFrame(core);
}

uint32_t wrapper_frame_counter(struct mCore* core) {
    return core->frameCounter(core);
}

uint8_t wrapper_read8(struct mCore* core, uint32_t addr) {
    return core->busRead8(core, addr);
}

uint32_t wrapper_read32(struct mCore* core, uint32_t addr) {
    return core->busRead32(core, addr);
}

/* Silent logger to suppress mGBA console spam. */
#include <mgba/core/log.h>

static void _silent_log(struct mLogger* logger, int cat, enum mLogLevel lvl, const char* fmt, va_list args) {
    (void)logger; (void)cat; (void)lvl; (void)fmt; (void)args;
}
static struct mLogger silent_logger = { .log = _silent_log };

void wrapper_silence_log(void) {
    mLogSetDefaultLogger(&silent_logger);
}
