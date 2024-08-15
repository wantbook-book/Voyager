async function craftStonePickaxe(bot) {
  // Check if there are enough cobblestones in the inventory
  const cobblestones = bot.inventory.count(mcData.itemsByName["cobblestone"].id);
  if (cobblestones < 3) {
    // Mine more cobblestones
    await mineBlock(bot, "cobblestone", 3 - cobblestones);
  }

  // Check if there is a crafting table in the inventory
  const craftingTable = bot.inventory.findInventoryItem(mcData.itemsByName["crafting_table"].id);
  if (!craftingTable) {
    // Explore until find a crafting table
    const foundCraftingTable = await exploreUntil(bot, new Vec3(1, 0, 1), 60, () => {
      const craftingTable = bot.findBlock({
        matching: mcData.blocksByName["crafting_table"].id,
        maxDistance: 32
      });
      return craftingTable;
    });
    if (!foundCraftingTable) {
      bot.chat("No crafting table nearby");
      return;
    }
  }

  // Place the crafting table near the player
  const craftingTablePosition = bot.entity.position.offset(1, 0, 0);
  await placeItem(bot, "crafting_table", craftingTablePosition);

  // Craft a stone pickaxe using cobblestones and the crafting table
  await craftItem(bot, "stone_pickaxe", 1, craftingTablePosition);
  bot.chat("Stone pickaxe crafted.");
}

// Call the function